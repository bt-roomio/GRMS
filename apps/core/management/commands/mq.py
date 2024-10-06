import json
import logging
import time

import pika
from django.conf import settings
from django.core.management.base import BaseCommand

from core.utils.random_letter import get_random_letter
from main.models import Device, DeviceCredentials
from shuttle.models import AttributeKv, TsKv, TsKvDictionary, TsKvLatest, Relation
from shuttle.utils.find_compatible_field import find_compatible_field
from shuttle.utils.get_non_null_field import get_non_null_field
from shuttle.utils.send_to_rabbitmq import send_to_rabbitmq_device_me

logger = logging.getLogger(__name__)
logger.critical("Now logging consumer command")

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT

rabbit_queues = {"toGRMSqueueName": "toGRMS", "fromGRMSqueueName": "fromGRMS"}


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
    # logger.critical(" [x] Received properties = %s ", properties)
    # logger.critical(" [x] Received method = %s ", method)

    msg = json.loads(body)

    device = Device.objects.filter(id=msg.get("sourceDeviceUUID")).first()
    data = msg.get("data")
    topic = msg.get("topic")
    ts = None

    print(time.time(), "HELLO" * 10, data)

    if topic.startswith("v1/devices/me/attributes/request"):
        shared_keys = data.get("sharedKeys")
        shared_keys = {key: "" for key in shared_keys.split(",")}
        attributes = AttributeKv.objects.filter(attribute_key__in=shared_keys.keys())
        for attribute in attributes:
            field, value = get_non_null_field(attribute)
            shared_keys[attribute.attribute_key] = value
        send_to_rabbitmq_device_me(device.id, shared_keys, topic.replace("request", "response"))

    if topic.startswith("v1/gateway/") and data and isinstance(data, dict):
        from_id = device.id
        for key, value in data.items():
            device, created = Device.objects.get_or_create(
                name=key,
                type="default",
                customer_id="0e43b252-8391-430d-807e-de64e0a63194",
                tenant_id="28c81921-f78e-4864-87d2-cec674f19d1c",
                device_profile_id="be17d30b-9785-4415-bfa5-e7fdaf19e37c",
            )
            if created:
                print("Device created")
                DeviceCredentials.objects.create(
                    credentials_type="ACCESS_TOKEN", credentials_id=get_random_letter(), device=device
                )

            Relation.objects.get_or_create(
                from_id_id=from_id,
                to_id_id=device.id,
                from_type="DEVICE",
                to_type="DEVICE",
                relation_type_group="COMMON",
                relation_type="Created",
            )
            data = value
            if data and isinstance(data, dict):
                if topic.endswith("attributes"):
                    print("save_attribute_kv")
                    save_attribute_kv(device, data)
                if topic.endswith("telemetry"):
                    print("save_telemetry_kv")
                    save_telemetry_kv(device, data, ts)

            elif data and isinstance(data, list) and all([isinstance(item, dict) for item in data]):
                for res in data:
                    if res.get("ts") and res.get("values"):
                        ts = res.get("ts")
                        res = res.get("values")
                    if topic.endswith("attributes"):
                        print("attributes")
                        save_attribute_kv(device, res)
                    if topic.endswith("telemetry"):
                        print("save_telemetry_kv")
                        save_telemetry_kv(device, res, ts)

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
        if topic == "v1/devices/me/attributes":
            save_attribute_kv(device, data)
        if topic == "v1/devices/me/telemetry":
            save_telemetry_kv(device, data, ts)

    elif data and isinstance(data, list) and all([isinstance(item, dict) for item in data]):
        for res in data:
            if topic == "v1/devices/me/attributes":
                print("save_attribute_kv")
                save_attribute_kv(device, res)
            if topic == "v1/devices/me/telemetry":
                print("save_telemetry_kv")
                save_telemetry_kv(device, res, ts)


def consume():
    channel = connect_to_rabbitmq()
    channel.basic_consume(queue=rabbit_queues["toGRMSqueueName"], on_message_callback=callback, auto_ack=True)

    logger.critical(f"Waiting for messages in topic. To exit press CTRL+C")
    channel.start_consuming()


def connect_to_rabbitmq():
    credentials = pika.PlainCredentials(RABBIT_LOGIN, RABBIT_PASSWORD)
    parameters = pika.ConnectionParameters(RABBIT_HOST, RABBIT_PORT, "/", credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    return channel


def save_telemetry_kv(device, data, ts):
    print(data)
    for key, item in find_compatible_field(data).items():
        fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
        ts_kv_dict, _ = TsKvDictionary.objects.get_or_create(key=key)
        fields[item[0]] = item[1]
        TsKv.objects.update_or_create(
            entity=device,
            key=ts_kv_dict.key_id,
            ts=ts or time.time(),
            defaults={**fields, "ts": ts or time.time()},
        )
        TsKvLatest.objects.update_or_create(
            entity=device,
            key=ts_kv_dict.key_id,
            defaults=fields,
        )
        time.sleep(0.1)


def save_attribute_kv(device, data):
    print(data)
    for key, item in find_compatible_field(data).items():
        fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
        fields[item[0]] = item[1]
        AttributeKv.objects.update_or_create(
            entity=device,
            attribute_type=AttributeKv.CLIENT_SCOPE,
            attribute_key=key,
            defaults={**fields, "entity_type": "DEVICE"},
        )
        time.sleep(0.1)

    server_data = {"active": True, "lastActivityTime": int(time.time())}
    for key, item in find_compatible_field(server_data).items():
        fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
        fields[item[0]] = item[1]
        AttributeKv.objects.update_or_create(
            entity=device,
            attribute_type=AttributeKv.SERVER_SCOPE,
            attribute_key=key,
            defaults={**fields, "entity_type": "DEVICE"},
        )
