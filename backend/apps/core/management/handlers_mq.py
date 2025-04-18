import json
import logging

from django.db import transaction
from pika.adapters.blocking_connection import BlockingChannel

from core.management.handle_fias import handle_fias
from core.rabbitmq.config import send_to_rabbitmq
from core.utils.date import unix_to_datetime
from core.utils.get_time import get_mil_sec
from core.utils.random_letter import get_random_letter
from main.models import Device, DeviceCredentials
from shuttle.models import AttributeKv, Relation, RPCMessage, TsKv, TsKvDictionary, TsKvLatest
from shuttle.utils.find_compatible_field import find_compatible_field

logger = logging.getLogger("django")
_tskv_dict_cache = {}


def get_tskv_dict(key):
    if key not in _tskv_dict_cache:
        obj, _ = TsKvDictionary.objects.get_or_create(key=key)
        _tskv_dict_cache[key] = obj
    return _tskv_dict_cache[key]


def handlers_mq(ch: BlockingChannel, body: bytes):
    msg = json.loads(body)
    device_id = msg.get("sourceDeviceUUID")
    device = Device.objects.filter(id=device_id).first()
    if not device:
        logger.warning("Device not found: %s", device_id)
        return

    topic = msg.get("topic", "")
    data = msg.get("data")

    if topic == "v1/gateway/rpc":
        _handle_rpc(data)
    elif topic in ("v1/gateway/connect", "v1/gateway/disconnect"):
        _handle_connect_disconnect(device, topic, data)
    elif topic.endswith("/attributes/request"):
        _handle_attribute_request(ch, device, topic, data)
    elif topic.endswith("/attributes"):
        _handle_attribute_saving(device, topic, data)
    elif topic.endswith("/telemetry"):
        _handle_telemetry(device, topic, data)
    else:
        logger.debug("Unhandled topic: %s", topic)


def _handle_rpc(data):
    RPCMessage.objects.filter(id=data.get("id"), received=False).update(received=True, additional_info=data.get("data"))


def _handle_connect_disconnect(device, topic, data):
    name = data.get("device")
    sub = Device.objects.filter(name=name, tenant_id=device.tenant_id, is_active=True).first()
    if not sub:
        sub = _get_or_create_device(name, device)
    connected = topic.endswith("connect")
    _update_activity_device(sub, connected)


def _handle_attribute_request(ch, device, topic, data):
    keys = data.get("sharedKeys") or data.get("keys") or []
    if isinstance(keys, str):
        keys = keys.split(",")
    sub_id = data.get("device")
    sub = Device.objects.filter(id=sub_id, tenant_id=device.tenant_id).first()
    if not sub:
        return
    attrs = AttributeKv.objects.filter(
        entity=sub, attribute_type=AttributeKv.SHARED_SCOPE, attribute_key__in=keys
    ).values("attribute_key", "bool_v", "str_v", "long_v", "dbl_v", "json_v")
    resp = {
        rec["attribute_key"]: next(
            v for v in (rec["bool_v"], rec["str_v"], rec["long_v"], rec["dbl_v"], rec["json_v"]) if v is not None
        )
        for rec in attrs
    }
    resp.update(device=str(sub.id), id=data.get("id"))
    send_to_rabbitmq(
        ch,
        {
            "targetDeviceUUID": str(device.id),
            "topic": topic.replace("request", "response"),
            "data": resp,
        },
    )


@transaction.atomic
def _handle_attribute_saving(device, topic, data):
    entries = data if isinstance(data, list) else [data]
    for item in entries:
        items = find_compatible_field(item)
        for key, (field, value) in items.items():
            defaults = {
                "bool_v": None,
                "str_v": None,
                "long_v": None,
                "dbl_v": None,
                "json_v": None,
                "entity_type": "DEVICE",
                "last_update_ts": get_mil_sec(),
            }
            defaults[field] = value
            AttributeKv.objects.update_or_create(
                entity=device,
                entity__tenant_id=device.tenant_id,
                attribute_type=(
                    AttributeKv.CLIENT_SCOPE
                    if "/devices/me/" in topic
                    else (
                        AttributeKv.CLIENT_SCOPE
                        if "/gateway/" in topic and "/attributes/" in topic
                        else AttributeKv.SERVER_SCOPE
                    )
                ),
                attribute_key=key,
                defaults=defaults,
            )
    _update_activity_gateway(device)


@transaction.atomic
def _handle_telemetry(device, topic, data):
    entries = []
    if isinstance(data, dict) and "ts" in data and "values" in data:
        entries.append((data["ts"], data["values"]))
    elif isinstance(data, list):
        for d in data:
            if "ts" in d and "values" in d:
                entries.append((d["ts"], d["values"]))
    if not entries:
        return
    mil_sec = get_mil_sec()
    ts_objs, latest_objs = [], []
    for ts, vals in entries:
        ts_dt = unix_to_datetime(ts)
        items = find_compatible_field(vals)
        for key, (field, value) in items.items():
            dict_obj = get_tskv_dict(key)
            ts_objs.append(TsKv(entity=device, key=dict_obj, ts=ts_dt, **{field: value}))
            latest_objs.append(TsKvLatest(entity=device, key=dict_obj, ts=mil_sec, **{field: value}))
            if key == "messageFromFIAS":
                handle_fias(value, device)
    TsKv.objects.bulk_create(ts_objs, ignore_conflicts=True)
    exists = TsKvLatest.objects.filter(entity=device, key__in=[o.key for o in latest_objs])
    exists_map = {e.key_id: e for e in exists}  # pyright: ignore
    to_create, to_update = [], []
    for obj in latest_objs:
        e = exists_map.get(obj.key_id)
        if e:
            for attr in ("ts", "bool_v", "str_v", "long_v", "dbl_v", "json_v"):
                setattr(e, attr, getattr(obj, attr))
            to_update.append(e)
        else:
            to_create.append(obj)
    if to_create:
        TsKvLatest.objects.bulk_create(to_create)
    if to_update:
        TsKvLatest.objects.bulk_update(to_update, ["ts", "bool_v", "str_v", "long_v", "dbl_v", "json_v"])
    _update_activity_gateway(device)


def _update_activity_gateway(device):
    if Device.objects.filter(id=device.id, tenant=device.tenant).exists():
        _update_activity_device(device, True)


def _update_activity_device(device, connected=True):
    mil_sec = get_mil_sec()
    attrs = {"active": ("bool_v", connected), "lastActivityTime": ("long_v", mil_sec)}
    for key, (field, val) in attrs.items():
        defaults = {field: val, "entity_type": "DEVICE", "last_update_ts": mil_sec}
        AttributeKv.objects.update_or_create(
            entity=device,
            entity__tenant_id=device.tenant_id,
            attribute_type=AttributeKv.SERVER_SCOPE,
            attribute_key=key,
            defaults=defaults,
        )


def _get_or_create_device(name, from_device):
    obj, created = Device.objects.get_or_create(
        name=name,
        tenant_id=from_device.tenant_id,
        is_active=True,
        type="default",
        defaults={"device_profile_id": from_device.device_profile_id},
    )
    if created:
        DeviceCredentials.objects.create(
            credentials_type="ACCESS_TOKEN", credentials_id=get_random_letter(), device=obj
        )
    Relation.objects.update_or_create(
        to_id_id=obj.id,
        from_type="DEVICE",
        to_type="DEVICE",
        relation_type_group="COMMON",
        relation_type="Created",
        defaults={"from_id_id": from_device.id, "updated_at": get_mil_sec()},
    )
    return obj
