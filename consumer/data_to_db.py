import threading
import json
from confluent_kafka import Consumer
from sqlalchemy import Table, Column, Integer, JSON

from db_conn import metadata, engine

worker_thread = None
stop_event = threading.Event()
table_cache = {}

def get_or_create_table(table_name: str):
    table_name = table_name.upper()
    if table_name not in table_cache:
        table = Table(
            table_name, metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('data', JSON),
            extend_existing=True
        )
        metadata.create_all(engine, tables=[table])
        table_cache[table_name] = table
    return table_cache[table_name]

def save_json_to_db(data, table_name: str):
    table = get_or_create_table(table_name)
    with engine.begin() as conn:
        conn.execute(table.insert().values(data=data))

def add_sum_and_flag(data):
    total_amount = sum(item["qty"] * item["unit_price"] for item in data["items"])
    data["total_amount"] = total_amount
    data["high_value"] = total_amount > 500
    return data

def kafka_consumer_worker(consumer: Consumer, topic: str, stops_event: threading.Event):
    get_or_create_table(table_name=topic)
    consumer.subscribe([topic])
    try:
        while not stops_event.is_set():
            msg = consumer.poll(1.0)
            if msg and not msg.error():
                data = json.loads(msg.value().decode('utf-8'))
                data = add_sum_and_flag(data)
                save_json_to_db(data=data, table_name=topic)
                print(f"Data saved to table {topic}: {data}")
    finally:
        consumer.close()

def start_background_consumer(consumer: Consumer, topic: str):
    global worker_thread, stop_event
    try:
        stop_event.clear()
        worker_thread = threading.Thread(target=kafka_consumer_worker, args=(consumer, topic, stop_event), daemon=True)
        worker_thread.start()
    except Exception as e:
        print(str(e))
        raise e

async def stop_background_consumer():
    global stop_event, worker_thread
    try:
        stop_event.set()
        if worker_thread is not None:
            worker_thread.join()
            return 1
        else:
            return 0
    except Exception as e:
        print(f"Error stopping background consumer: {str(e)}")
        return -1