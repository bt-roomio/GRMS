import json
import logging
import time

import pika
from django.conf import settings
from django.core.management.base import BaseCommand
from main.models import Device
from shuttle.models import TsKv, TsKvDictionary
from shuttle.utils.find_compatible_field import find_compatible_field

logger = logging.getLogger(__name__)
logger.critical("Now logging consumer command")

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT

gatewayPublish = [
    "v1/gateway/connect",
    "v1/gateway/disconnect",
    "v1/gateway/attributes",
    "v1/gateway/attributes/request" "v1/gateway/attributes/response",
    "v1/gateway/attributes/request/+",
    "v1/gateway/attributes/response/+",
    "v1/gateway/telemetry",
    "v1/devices/me/telemetry",
    "v1/devices/me/attributes",
]


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def handle(self, *args, **options):
        self.stdout.write("consumer command")
        logger.critical("CorrelaotrConfig.ready")
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future = executor.submit(consume)
            try:
                future.result()
                logger.critical("OOOOOOOOOOOOOOOOOOOOOOOOO thread completed! OOOOOOOOOOOOOOOOOOOO")
            except Exception as e:
                logger.error("OOOOOOOOOOOOOOOOOOOOOO error %s OOOOOOOOOOOOOOOOOOOO", e, exc_info=1)

        self.stdout.write("Successfully started daemon ")


def callback(ch, method, properties, body):
    logger.critical(" Received body = %s ", body)
    logger.critical(" [x] Received properties = %s ", properties)
    logger.critical(" [x] Received method = %s ", method)
    routing_key = method.routing_key
    msg = json.loads(body)

    device = Device.objects.filter(id=msg.get("sourceDeviceUUID")).first()
    data = msg.get("data")
    ts = None

    if not device:
        print("Device not found")
        return

    if not data:
        print("No data found")
        return

    if data and isinstance(data, dict) and data.get("ts") and data.get("values"):
        ts = data.get("ts")
        data = data.get("values")

    if data and isinstance(data, dict):
        if data and isinstance(data, dict):
            if routing_key == "v1/devices/me/telemetry":
                for key, item in find_compatible_field(data).items():
                    fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
                    ts_kv_dict, _ = TsKvDictionary.objects.get_or_create(key=key)
                    fields[item[0]] = item[1]

                    ts_kv = TsKv.objects.update_or_create(
                        entity=device,
                        key=ts_kv_dict.key_id,
                        ts=ts or time.time(),
                        defaults={**fields, "ts": ts or time.time()},
                    )
                    time.sleep(0.1)

    elif data and isinstance(data, list) and all([isinstance(item, dict) for item in data]):
        for res in data:
            if routing_key == "v1/devices/me/telemetry":
                for key, item in find_compatible_field(res).items():
                    fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
                    ts_kv_dict, _ = TsKvDictionary.objects.get_or_create(key=key)
                    fields[item[0]] = item[1]
                    ts_kv = TsKv.objects.update_or_create(
                        entity=device,
                        key=ts_kv_dict.key_id,
                        ts=ts or time.time(),
                        defaults={**fields, "ts": ts or time.time()},
                    )
                    time.sleep(0.1)

    print(json.loads(body), routing_key)


def consume():
    channel = connect_to_rabbitmq()
    for topic in gatewayPublish:
        channel.basic_consume(queue=topic, on_message_callback=callback, auto_ack=True)

        logger.critical(f"Waiting for messages in {topic}. To exit press CTRL+C")
    channel.start_consuming()


def connect_to_rabbitmq():
    credentials = pika.PlainCredentials(RABBIT_LOGIN, RABBIT_PASSWORD)
    parameters = pika.ConnectionParameters(RABBIT_HOST, RABBIT_PORT, "/", credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    # for topic in gatewayPublish:
    #     channel.queue_declare(queue=topic)
    return channel


def test():
    # "v1/devices/me/telemetr -> TsKv"
    fake_data = {
        "sourceDeviceUUID": "47aef21b-6cc9-4ec5-8573-1a6f491940c0",
        "data": {"ts": 1451649600512, "values": {"key1": "222", "key2": True}},
    }
    routing_key = "v1/devices/me/telemetry"
    msg = fake_data

    device = Device.objects.filter(id=msg.get("sourceDeviceUUID")).first()
    data = msg.get("data")
    ts = None

    if not device:
        print("Device not found")
        return

    if not data:
        print("No data found")
        return

    if data and isinstance(data, dict) and data.get("ts") and data.get("values"):
        ts = data.get("ts")
        data = data.get("values")

    if data and isinstance(data, dict):
        if data and isinstance(data, dict):
            if routing_key == "v1/devices/me/telemetry":
                for key, item in find_compatible_field(data).items():
                    fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
                    ts_kv_dict, _ = TsKvDictionary.objects.get_or_create(key=key)
                    fields[item[0]] = item[1]

                    ts_kv = TsKv.objects.update_or_create(
                        entity=device,
                        key=ts_kv_dict.key_id,
                        ts=ts or time.time(),
                        defaults={**fields, "ts": ts or time.time()},
                    )
                    time.sleep(0.1)

    # data = msg.get("data")
    # ts = None

    # if not device:
    #     print("Device not found")
    #     return

    # if not data:
    #     print("No data found")
    #     return

    # if data and isinstance(data, dict) and data.get("ts") and data.get("values"):
    #     data = data.get("values")
    #     ts = data.get("ts")

    # if data and isinstance(data, dict):
    #     if routing_key == "v1/devices/me/telemetry":
    #         for key, item in find_compatible_field(data).items():
    #             ts_kv_dict, _ = TsKvDictionary.objects.get_or_create(key=key)
    #             field = item[0]
    #             value = item[1]
    #             ts_kv = TsKv.objects.create(entity=device, key=ts_kv_dict.key_id, ts=ts or time.time())
    #             if ts_kv:
    #                 setattr(ts_kv, field, value)
    #                 ts_kv.save()
    #             time.sleep(0.1)

    # elif data and isinstance(data, list) and all([isinstance(item, dict) for item in data]):
    #     for res in data:
    #         if routing_key == "v1/devices/me/telemetry":
    #             for key, item in find_compatible_field(res).items():
    #                 ts_kv_dict, _ = TsKvDictionary.objects.get_or_create(key=key)
    #                 field = item[0]
    #                 value = item[1]
    #                 ts_kv = TsKv.objects.create(entity=device, key=ts_kv_dict.key_id, ts=ts or time.time())
    #                 if ts_kv:
    #                     setattr(ts_kv, field, value)
    #                     ts_kv.save()
    #                 time.sleep(0.1)
