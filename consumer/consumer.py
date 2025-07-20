import json
import os
import socket
from contextlib import asynccontextmanager
from datetime import timedelta, timezone, datetime
from http import HTTPStatus
from typing import List, Dict, Annotated

import jwt
from authlib.jose import JsonWebToken, JoseError
from confluent_kafka import Consumer, Message
from confluent_kafka.admin import AdminClient
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import text

from data_to_db import start_background_consumer
from data_to_db import stop_background_consumer, worker_thread
from db_conn import engine

SECRET_KEY = "b7cf3d0a3063672ffbe7fa6ff5662339e2ae6d92ea1fa68db3008b74594241bb"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

print("Starting Kafka Consumer")
consumer = Consumer({
    'bootstrap.servers': 'kafka_broker',
    'group.id': 'prediction_consumer',
    'auto.offset.reset': 'earliest'
})

conf = {'bootstrap.servers': 'kafka_broker:9092',
        'client.id': socket.gethostname()}
admin_client = AdminClient(conf)

@asynccontextmanager
async def enable_kafka(app: FastAPI):
    yield
    consumer.close()

app = FastAPI(title="Kafka Consumer", lifespan=enable_kafka)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User:
    username =  str(os.getenv('USERNAME'))
    password = str(os.getenv('PASSWORD'))


def authenticate_user(username: str, password: str):
    print(f"Authenticating user: {username}")
    print(f"User password: {password}")
    user = User
    if user.username != username:
        return False
    if user.password != password:
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

class Token(BaseModel):
    access_token: str
    token_type: str

# schema for Token Data
class TokenData(BaseModel):
    userid: str | None = None

def validate_token(
        token: Annotated[str, Depends(oauth2_scheme)]
):
    credentials_exception = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        jwt = JsonWebToken([ALGORITHM])
        payload = jwt.decode(token, SECRET_KEY)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(userid=username)
    except JoseError:
        raise credentials_exception
    user = User
    if user.username != token_data.userid:
        raise credentials_exception
    return True


@app.post("/token")
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    print(f"User: {user}")
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


router = APIRouter(
    dependencies=[Depends(validate_token)]
)

@router.get(path="/get_topic_list")
def list_topics():
    metadata = admin_client.list_topics(timeout=10)
    return {"topics": list(metadata.topics.keys())}

topics_available: List[str] = [item for item in list_topics().get("topics") if not item.startswith('_')]
@router.post(path="/subscribe_topic")
def subscribe_topic(
        # topic = Query(enum=topics_available),
        topic: str
):
    try:
        consumer.subscribe([topic])
        return f"Subscribed to topic: {topic}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(path="/get_data")
def get_data():
    try:
        msg: Message = consumer.poll(1.0)

        if msg is None:
            raise HTTPException(status_code=404, detail={"data": "No data available"})
        if msg.error():
            raise HTTPException(status_code=500, detail="Consumer error: {}".format(msg.error()))

        return json.loads(msg.value().decode('utf-8'))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(path="/print_data", include_in_schema=False)
def print_data(
        data: Dict,
):
    try:
        data = get_data()
        data = json.dumps(data)
        return data.json()
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(path="/save_stream_data_to_db")
async def save_stream_data_to_db(
        background_tasks: BackgroundTasks,
        topic: str,
):
    try:
        if worker_thread is not None and worker_thread.is_alive():
            return {"message": "Background consumer is already running."}
        background_tasks.add_task(start_background_consumer, consumer=consumer, topic=topic)
        return {"message": "Background task started to save stream data to the database."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(path="/stop_data_stream")
async def stop_data_stream():
    try:
        status = await stop_background_consumer()
        if status == 1:
            return"Order data stream stopped successfully"
        elif status == 0:
            return "No active consumer to stop"
        else:
            raise HTTPException(status_code=500, detail="Error stopping background consumer")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=e)

@router.get(path="/get_vendors")
def get_vendors():
    try:
        query = """
        SELECT DISTINCT data->>'vendor_id' AS vendor_id
        FROM "ORDERS"
        WHERE data->>'vendor_id' IS NOT NULL
        """
        with engine.begin() as conn:
            result = conn.execute(text(query)).mrouterings()
            vendors = [row['vendor_id'] for row in result if row['vendor_id']]
            return {"vendors": vendors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(path="/metrics")
def metrics(
        vendor_id: str = None,
):
    try:
        query = """
        SELECT
            data->>'vendor_id' AS vendor_id,
            COUNT(*) AS total_orders,
            SUM(
                (SELECT SUM((item->>'qty')::int * (item->>'unit_price')::numeric)
                 FROM jsonb_array_elements((data->'items')::jsonb) AS item)
            ) AS total_revenue,
            COUNT(*) FILTER (
                WHERE (SELECT SUM((item->>'qty')::int * (item->>'unit_price')::numeric)
                       FROM jsonb_array_elements((data->'items')::jsonb) AS item) > 1000
            ) AS high_value_orders,
            COUNT(*) FILTER (
                WHERE EXISTS (
                    SELECT 1 FROM jsonb_array_elements((data->'items')::jsonb) AS item
                    WHERE (item->>'qty')::int > 100
                )
            ) AS anomalous_orders,
            (
                SELECT json_object_agg(order_date, order_count)
                FROM (
                    SELECT
                        to_char((data->>'timestamp')::timestamp, 'YYYY-MM-DD') AS order_date,
                        COUNT(*) AS order_count
                    FROM "ORDERS"
                    WHERE data->>'vendor_id' = :vendor_id
                      AND (data->>'timestamp')::timestamp >= NOW() - INTERVAL '7 days'
                    GROUP BY order_date
                ) AS daily
            ) AS last_7_days_volume
        FROM "ORDERS"
        WHERE data->>'vendor_id' = :vendor_id
        GROUP BY data->>'vendor_id';
        """
        with engine.begin() as conn:
            result = conn.execute(text(query), {"vendor_id": vendor_id})
            row = result.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Vendor not found")
            columns = result.keys()
            data = dict(zip(columns, row))
            return data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(router)