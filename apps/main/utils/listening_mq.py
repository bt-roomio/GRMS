import json
import threading
import time

import pika
from django.conf import settings

from core.utils.random_letter import get_random_letter
from main.models import Device, DeviceCredentials
from shuttle.models import RPCMessage, AttributeKv, TsKvDictionary, TsKv, TsKvLatest, Relation
from shuttle.utils.find_compatible_field import find_compatible_field
from shuttle.utils.get_non_null_field import get_non_null_field
from shuttle.utils.send_to_rabbitmq import send_to_rabbitmq_device_me

ROUTING_KEY = "toGRMS"
EXCHANGE = ""
THREADS = 5

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT

rabbit_queues = {"toGRMSqueueName": "toGRMS", "fromGRMSqueueName": "fromGRMS"}


class MQListener(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        credentials = pika.PlainCredentials(RABBIT_LOGIN, RABBIT_PASSWORD)
        parameters = pika.ConnectionParameters(RABBIT_HOST, RABBIT_PORT, "/", credentials)
        connection = pika.BlockingConnection(parameters)
        self.channel = connection.channel()
        self.channel.basic_consume(
            queue=rabbit_queues["toGRMSqueueName"], on_message_callback=self.callback, auto_ack=True
        )

    def callback(self, channel, method, properties, body):
        print(" [x] Received %r" % body)
        msg = json.loads(body)
        device = Device.objects.filter(id=msg.get("sourceDeviceUUID")).first()
        data = msg.get("data")
        topic = msg.get("topic")
        ts = None

        if topic == "v1/gateway/rpc":
            rpc_msg = RPCMessage.objects.filter(id=data.get("id")).first()
            if rpc_msg:
                rpc_msg.received = True
                rpc_msg.additional_info = data.get("data")
                rpc_msg.save()
        elif topic == "v1/gateway/connect":
            device = Device.objects.filter(name=data.get("device")).first()
            update_activity_device(device)
        elif topic == "v1/gateway/disconnect":
            device = Device.objects.filter(name=data.get("device")).first()
            update_activity_device(device, connected=False)

        elif topic.startswith("v1/devices/me/attributes/request") or topic.startswith("v1/gateway/attributes/request"):
            # print(f"Topic: {topic}, {data}")
            shared_keys = data.get("sharedKeys", []) or data.get("keys", [])
            shared_keys = shared_keys.split(",")
            attributes = AttributeKv.objects.filter(
                attribute_key__in=shared_keys, attribute_type=AttributeKv.SHARED_SCOPE, entity_id=device.id
            )
            response_keys = {}
            for attribute in attributes:
                field, value = get_non_null_field(attribute)
                response_keys[attribute.attribute_key] = value
            send_to_rabbitmq_device_me(device.id, response_keys, topic.replace("request", "response"), data.get("id"))
        elif topic.startswith("v1/gateway/") and data and isinstance(data, dict):
            for key, value in data.items():
                device_to_id = get_or_create_device(key, device)
                data = value
                if data and isinstance(data, dict):
                    if topic.endswith("attributes"):
                        # print("save_attribute_kv", data)
                        save_attribute_kv(device_to_id, data)
                    if topic.endswith("telemetry"):
                        # print("save_telemetry_kv", data)
                        save_telemetry_kv(device_to_id, data, ts)

                elif data and isinstance(data, list) and all([isinstance(item, dict) for item in data]):
                    for res in data:
                        if res.get("ts") and res.get("values"):
                            ts = res.get("ts")
                            res = res.get("values")
                        if topic.endswith("attributes"):
                            # print("save_attribute_kv")
                            save_attribute_kv(device_to_id, res)
                        if topic.endswith("telemetry"):
                            # print("save_telemetry_kv")
                            save_telemetry_kv(device_to_id, res, ts)

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
                # print("save_attribute_kv")
                save_attribute_kv(device, data)
            if topic == "v1/devices/me/telemetry":
                # print("save_telemetry")
                save_telemetry_kv(device, data, ts)

        elif data and isinstance(data, list) and all([isinstance(item, dict) for item in data]):
            for res in data:
                if topic == "v1/devices/me/attributes":
                    # print("save_attribute_kv")
                    save_attribute_kv(device, res)
                if topic == "v1/devices/me/telemetry":
                    # print("save_telemetry")
                    save_telemetry_kv(device, res, ts)

        channel.basic_ack(delivery_tag=method.delivery_tag)

    def run(self):
        print("Inside LogginService:  Created Listener ")
        self.channel.start_consuming()


def save_telemetry_kv(device, data, ts):
    for key, item in find_compatible_field(data).items():
        fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
        ts_kv_dict, _ = TsKvDictionary.objects.get_or_create(key=key)
        fields[item[0]] = item[1]
        TsKv.objects.update_or_create(
            entity=device,
            key=ts_kv_dict.key_id,
            ts=ts or int(time.time()),
            defaults=fields,
        )
        TsKvLatest.objects.update_or_create(
            entity=device,
            key=ts_kv_dict.key_id,
            defaults={**fields, "ts": int(time.time())},
        )
        time.sleep(0.1)

    update_activity_gateway(device)


def save_attribute_kv(device, data):
    for key, item in find_compatible_field(data).items():
        fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
        fields[item[0]] = item[1]
        AttributeKv.objects.update_or_create(
            entity=device,
            attribute_type=AttributeKv.CLIENT_SCOPE,
            attribute_key=key,
            defaults={**fields, "entity_type": "DEVICE", "last_update_ts": int(time.time())},
        )
        time.sleep(0.1)

    update_activity_gateway(device)  # Ask for this line, when topic /attribute, should check for gateway then update ?


def update_activity_gateway(device):
    is_gateway = Device.objects.filter(id=device.id, additional_info__gateway=True).exists()
    if is_gateway:
        update_activity_device(device)


def update_activity_device(device, connected=True):
    server_data = {"active": connected, "lastActivityTime": int(time.time())}
    for key, item in find_compatible_field(server_data).items():
        fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
        fields[item[0]] = item[1]
        AttributeKv.objects.update_or_create(
            entity=device,
            attribute_type=AttributeKv.SERVER_SCOPE,
            attribute_key=key,
            defaults={**fields, "entity_type": "DEVICE", "last_update_ts": int(time.time())},
        )


def get_or_create_device(name, from_id):
    device_to_id, created = Device.objects.get_or_create(
        name=name,
        type="default",
        tenant_id=from_id.tenant_id,
        device_profile_id=from_id.device_profile_id,
    )
    if created:
        print("Device created")
        DeviceCredentials.objects.create(
            credentials_type="ACCESS_TOKEN", credentials_id=get_random_letter(), device=device_to_id
        )

    Relation.objects.get_or_create(
        from_id=from_id,
        to_id_id=device_to_id.id,
        from_type="DEVICE",
        to_type="DEVICE",
        relation_type_group="COMMON",
        relation_type="Created",
    )

    return device_to_id
