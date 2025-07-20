import json
import os
import socket
from datetime import datetime, timezone, timedelta
from http import HTTPStatus
from typing import List, Dict, Annotated

import jwt
from authlib.jose import JsonWebToken, JoseError
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient
from confluent_kafka.cimpl import NewTopic
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from stream_data import start_production, stop_production

SECRET_KEY = "b7cf3d0a3063672ffbe7fa6ff5662339e2ae6d92ea1fa68db3008b74594241bb"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

conf = {'bootstrap.servers': 'kafka_broker:9092',
        'client.id': socket.gethostname()}

admin_client = AdminClient(conf)
producer = Producer(conf)

app = FastAPI(title="Kafka Producer")

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

# # Kafka producer configuration
# producer = KafkaProducer(bootstrap_servers='kafka1:9092')
def acked(err, msg):
    if err is not None:
        print("Failed to deliver message: %s: %s" % (str(msg), str(err)))
    else:
        print("Message produced: %s" % (str(msg)))

@router.get(path="/get_topic_list")
def list_topics():
    print("---> Listing topics")
    metadata = admin_client.list_topics(timeout=10)
    print(f"metadata: {metadata}")
    print(f"---> topics: {metadata.topics}")
    print(f"---> type: {type(metadata.topics.keys())}")
    return {"topics": list(metadata.topics.keys())}

topics_available: List[str] = [item for item in list_topics().get("topics") if not item.startswith('_')]

@router.post(path="/create_topic")
def create_topics(
        topic_name: str,
        num_partitions: int = Query(default=1, ge=1, le=100, description="Number of partitions for the topic"),
        replication_factor: int = Query(default=1, ge=1, le=3, description="Replication factor for the topic"),
        # topic_configs: Dict[str, str] = Query(
        #     default={},
        #     description="Custom configurations for the topic in key-value pairs"
        # ),
):
    try:
        new_topic = NewTopic(
            topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            # config=topic_configs,
        )

        futures = admin_client.create_topics([new_topic])

        for topic, future in futures.items():
            future.result()
            return f"Topic '{topic}' created successfully with custom configurations!"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



ord_data = {
    "vendor_id": "V001",
    "order_id": "ORD123",
    "items": [
        { "sku": "SKU1", "qty": 2, "unit_price": 120 },
        { "sku": "SKU2", "qty": 1, "unit_price": 50 }
    ],
    "timestamp": "2025-07-04T14:00:00Z"
}

@router.post(path="/send_data")
def send_data(
        data: Dict,
        topic:str,
        # topic: str
):
    try:
        producer.produce(topic=str(topic), key="data", value=json.dumps(data), callback=acked)
        producer.poll(1)
        return f"Data: {data} send successfully"
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=e)


@router.post(path="/start_data_stream")
async def start_data_stream(
        background_task: BackgroundTasks,
        topic: str = Query(default="orders", description="Topic to produce data to"),
):
    try:
        background_task.add_task(start_production, producer=producer, topic="orders", key="order")
        return "Order data stream started successfully"
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=e)

@router.post(path="/stop_data_stream")
async def stop_data_stream():
    try:
        await stop_production()
        return"Order data stream stopped successfully"
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=e)

app.include_router(router)