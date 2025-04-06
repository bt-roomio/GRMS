import json
import logging

from pika.adapters.blocking_connection import BlockingChannel

from core.management.handle_fias import handle_fias
from core.rabbitmq.config import send_to_rabbitmq
from core.utils.get_time import get_mil_sec
from core.utils.random_letter import get_random_letter
from main.models import Device, DeviceCredentials
from shuttle.models import AttributeKv, Relation, RPCMessage, TsKv, TsKvDictionary, TsKvLatest
from shuttle.utils.find_compatible_field import find_compatible_field
from shuttle.utils.get_non_null_field import get_non_null_field

logger = logging.getLogger("django")


def handlers_mq(ch: BlockingChannel, body: bytes):
    msg = json.loads(body)
    logger.info(msg)

    device = Device.objects.filter(id=msg.get("sourceDeviceUUID")).first()
    if not device:
        logger.warning("Device not found!")
        return

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
        device = (
            Device.objects.is_active()  # pyright: ignore
            .filter(name=data.get("device"), tenant_id=device.tenant_id)
            .first()
        )
        update_activity_device(device)
    elif topic == "v1/gateway/disconnect":
        device = (
            Device.objects.is_active()  # pyright: ignore
            .filter(name=data.get("device"), tenant_id=device.tenant_id)
            .first()
        )
        update_activity_device(device, connected=False)

    elif topic.startswith("v1/gateway/attributes/request") and device:
        shared_keys = data.get("sharedKeys", []) or data.get("keys", [])
        shared_keys = shared_keys.split(",")
        sub_device = Device.objects.filter(tenant_id=device.tenant_id, name=data.get("device")).first()
        if not sub_device:
            return

        attributes = AttributeKv.objects.filter(
            attribute_key__in=shared_keys, attribute_type=AttributeKv.SHARED_SCOPE, entity_id=sub_device.id
        )
        message = {
            "targetDeviceUUID": str(device.id),
            "topic": topic.replace("request", "response"),
            "data": {},
        }
        for attribute in attributes:
            _, value = get_non_null_field(attribute)
            message["data"][attribute.attribute_key] = value
        message["data"]["device"] = str(sub_device.id)
        message["data"]["id"] = data.get("id")
        send_to_rabbitmq(ch, message)

    elif topic.startswith("v1/devices/me/attributes/request") and device:
        shared_keys = data.get("sharedKeys", []) or data.get("keys", [])
        shared_keys = shared_keys.split(",") if shared_keys else []
        attributes = AttributeKv.objects.filter(attribute_type=AttributeKv.SHARED_SCOPE, entity_id=device.id)
        attributes = attributes.filter(attribute_key__in=shared_keys) if shared_keys else attributes

        message = {
            "targetDeviceUUID": str(device.id),
            "topic": topic.replace("request", "response"),
            "data": {},
        }
        for attribute in attributes:
            _, value = get_non_null_field(attribute)
            message["data"][attribute.attribute_key] = value
        send_to_rabbitmq(ch, message)

    elif topic.startswith("v1/gateway/") and data and isinstance(data, dict):
        for key, value in data.items():
            device_to_id = get_or_create_device(key, device)
            data = value
            if data and isinstance(data, dict):
                if topic.endswith("attributes"):
                    save_attribute_kv(device_to_id, data)
                if topic.endswith("telemetry"):
                    save_telemetry_kv(device_to_id, data, ts)

            elif data and isinstance(data, list) and all([isinstance(item, dict) for item in data]):
                for res in data:
                    if res.get("ts") and res.get("values"):
                        ts = res.get("ts")
                        res = res.get("values")
                    if topic.endswith("attributes"):
                        save_attribute_kv(device_to_id, res)
                    if topic.endswith("telemetry"):
                        save_telemetry_kv(device_to_id, res, ts)

    if not device:
        logger.warn("Device not found")
        return

    if not data:
        logger.warn("No data found")
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
                save_attribute_kv(device, res)
            if topic == "v1/devices/me/telemetry":
                save_telemetry_kv(device, res, ts)


def save_telemetry_kv(device, data, ts):
    for key, item in find_compatible_field(data).items():
        fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
        ts_kv_dict, _ = TsKvDictionary.objects.get_or_create(key=key)
        fields[item[0]] = item[1]
        TsKv.objects.update_or_create(
            entity=device,
            key=ts_kv_dict,
            ts=ts or get_mil_sec(),
            defaults=fields,
        )
        TsKvLatest.objects.update_or_create(
            entity=device,
            key=ts_kv_dict,
            defaults={**fields, "ts": get_mil_sec()},
        )
    if data.get("messageFromFIAS"):
        handle_fias(data.get("messageFromFIAS"), device)
    update_activity_gateway(device)


def save_attribute_kv(device, data):
    for key, item in find_compatible_field(data).items():
        fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
        fields[item[0]] = item[1]
        AttributeKv.objects.update_or_create(
            entity=device,
            entity__tenant_id=device.tenant_id,
            attribute_type=AttributeKv.CLIENT_SCOPE,
            attribute_key=key,
            defaults={**fields, "entity_type": "DEVICE", "last_update_ts": get_mil_sec()},
        )

    update_activity_gateway(device)


def update_activity_gateway(device):
    is_gateway = Device.objects.filter(id=device.id, tenant=device.tenant).exists()
    if is_gateway:
        update_activity_device(device)


def update_activity_device(device, connected=True):
    server_data = {"active": connected, "lastActivityTime": get_mil_sec()}
    for key, item in find_compatible_field(server_data).items():
        fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
        fields[item[0]] = item[1]
        AttributeKv.objects.update_or_create(
            entity=device,
            entity__tenant_id=device.tenant_id,
            attribute_type=AttributeKv.SERVER_SCOPE,
            attribute_key=key,
            defaults={**fields, "entity_type": "DEVICE", "last_update_ts": get_mil_sec()},
        )


def get_or_create_device(name, from_id):
    device_to_id, created = Device.objects.get_or_create(
        name=name,
        is_active=True,
        type="default",
        tenant_id=from_id.tenant_id,
        defaults={"device_profile_id": from_id.device_profile_id},
    )
    if created:
        DeviceCredentials.objects.create(
            credentials_type="ACCESS_TOKEN", credentials_id=get_random_letter(), device=device_to_id
        )

    Relation.objects.update_or_create(
        to_id_id=device_to_id.id,
        from_type="DEVICE",
        to_type="DEVICE",
        relation_type_group="COMMON",
        relation_type="Created",
        defaults={"from_id_id": from_id.id, "updated_at": get_mil_sec()},
    )

    return device_to_id
