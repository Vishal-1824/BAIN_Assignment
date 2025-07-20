import asyncio
import json
import random
import string
from datetime import datetime, timezone, timedelta

from confluent_kafka import Producer

def random_timestamp():
    base_date = datetime(2025, 7, 1)
    random_days = random.randint(0, 30)
    random_time = timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
    return (base_date + timedelta(days=random_days) + random_time).isoformat() + "Z"

def random_order():
    vendor_id = 'V00' + ''.join(random.choices(string.digits, k=1))
    order_id = 'ORD' + ''.join(random.choices(string.digits, k=3))
    num_items = random.randint(1, 5)
    items = []
    for _ in range(num_items):
        sku = 'SKU' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        qty = random.randint(1, 10)
        unit_price = random.randint(10, 500)
        items.append({
            "sku": sku,
            "qty": qty,
            "unit_price": unit_price
        })
    timestamp = random_timestamp()
    return {
        "vendor_id": vendor_id,
        "order_id": order_id,
        "items": items,
        "timestamp": timestamp
    }

_running_event = asyncio.Event()
_production_task = None

def acked(err, msg):
    if err is not None:
        print("Failed to deliver message: %s: %s" % (str(msg), str(err)))
    else:
        print("Message produced: %s" % (str(msg)))

async def _produce_orders(
        producer: Producer,
        topic: str,
        key: str
):
    while _running_event.is_set():
        order = random_order()
        producer.produce(topic=topic, key=key, value=json.dumps(order), callback=acked)
        producer.poll(1)
        await asyncio.sleep(1)

async def start_production(
        producer: Producer,
        topic: str,
        key: str
):
    global _production_task
    if _production_task and not _production_task.done():
        return "Production already in progress"
    _running_event.set()
    _production_task = asyncio.create_task(
        _produce_orders(producer=producer, topic=topic, key=key)
    )
    return "Production started"

async def stop_production():
    global _production_task
    _running_event.clear()
    if _production_task is not None:
        await _production_task
        _production_task = None
    return "Production stopped"
