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
    """Cache or create TsKvDictionary entries to minimize DB hits."""
    if key not in _tskv_dict_cache:
        obj, _ = TsKvDictionary.objects.get_or_create(key=key)
        _tskv_dict_cache[key] = obj
    return _tskv_dict_cache[key]


def handlers_mq(ch: BlockingChannel, body: bytes):
    msg = json.loads(body)
    logger.info(msg)
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
        _handle_attribute_request(ch, device, data)
    elif topic.endswith("/attributes"):
        _handle_attribute_saving(device, data)
    elif topic.endswith("/telemetry"):
        _handle_telemetry(device, data)
    else:
        logger.debug("Unhandled topic: %s", topic)


def _handle_rpc(data):
    """Mark RPCMessage as received."""
    RPCMessage.objects.filter(id=data.get("id"), received=False).update(
        received=True,
        additional_info=data.get("data"),
    )


def _handle_connect_disconnect(device, topic, data):
    """Handle gateway connect/disconnect events."""
    name = data.get("device")
    sub = Device.objects.filter(
        name__iexact=name,
        tenant_id=device.tenant_id,
        is_active=True,
    ).first()
    if not sub:
        sub = _get_or_create_device(name, device)
    connected = topic.endswith("connect")
    _update_activity_device(sub, connected)


def _handle_attribute_request(ch, device, data):
    """Respond to shared-attributes request from gateway."""
    keys = data.get("sharedKeys") or data.get("keys") or []
    if isinstance(keys, str):
        keys = keys.split(",")
    sub_name = data.get("device")
    sub = Device.objects.filter(
        name__iexact=sub_name,
        tenant_id=device.tenant_id,
        is_active=True,
    ).first()
    if not sub:
        # create sub-device if missing
        sub = _get_or_create_device(sub_name, device)
    attrs = AttributeKv.objects.filter(
        entity=sub,
        attribute_type=AttributeKv.SHARED_SCOPE,
        attribute_key__in=keys,
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
        {"targetDeviceUUID": str(device.id), "topic": "v1/gateway/attributes/response", "data": resp},
    )


@transaction.atomic
def _handle_attribute_saving(device, data):
    """Save incoming attribute key-values in CLIENT_SCOPE."""
    entries = data if isinstance(data, list) else [data]
    ts_now = get_mil_sec()
    for entry in entries:
        for key, (field, value) in find_compatible_field(entry).items():
            defaults = {
                "bool_v": None,
                "str_v": None,
                "long_v": None,
                "dbl_v": None,
                "json_v": None,
                "entity_type": "DEVICE",
                "last_update_ts": ts_now,
            }
            defaults[field] = value
            AttributeKv.objects.update_or_create(
                entity=device,
                entity__tenant_id=device.tenant_id,
                attribute_type=AttributeKv.CLIENT_SCOPE,
                attribute_key=key,
                defaults=defaults,
            )
    _update_activity_gateway(device)


@transaction.atomic
def _handle_telemetry(device, data):
    """Bulk-save telemetry and maintain latest values."""
    # Collect (timestamp, values) pairs
    entries = []
    if isinstance(data, dict) and "ts" in data and "values" in data:
        entries.append((data["ts"], data["values"]))
    elif isinstance(data, list):
        entries.extend((d["ts"], d["values"]) for d in data if "ts" in d and "values" in d)
    if not entries:
        return

    ts_now = get_mil_sec()
    historical, latest = [], []

    for ts_ms, vals in entries:
        ts_dt = unix_to_datetime(ts_ms)
        for key, (field, value) in find_compatible_field(vals).items():
            dict_obj = get_tskv_dict(key)
            historical.append(TsKv(entity=device, key=dict_obj, ts=ts_dt, **{field: value}))
            latest.append(TsKvLatest(entity=device, key=dict_obj, ts=ts_now, **{field: value}))
            if key == "messageFromFIAS":
                handle_fias(value, device)

    # Bulk insert historical telemetry
    TsKv.objects.bulk_create(historical, ignore_conflicts=True)

    # De-duplicate by key and split updates vs creates
    unique_latest = {obj.key_id: obj for obj in latest}
    existing = TsKvLatest.objects.filter(
        entity=device,
        key_id__in=unique_latest.keys(),
    )
    existing_map = {e.key_id: e for e in existing}  # pyright: ignore

    to_create, to_update = [], []
    for key_id, obj in unique_latest.items():
        if key_id in existing_map:
            existing_obj = existing_map[key_id]
            for attr in ("ts", "bool_v", "str_v", "long_v", "dbl_v", "json_v"):
                setattr(existing_obj, attr, getattr(obj, attr))
            to_update.append(existing_obj)
        else:
            to_create.append(obj)

    if to_create:
        TsKvLatest.objects.bulk_create(to_create)
    if to_update:
        TsKvLatest.objects.bulk_update(to_update, ["ts", "bool_v", "str_v", "long_v", "dbl_v", "json_v"])

    _update_activity_gateway(device)


def _update_activity_gateway(device):
    if Device.objects.filter(id=device.id, tenant_id=device.tenant_id).exists():
        _update_activity_device(device)


def _update_activity_device(device, connected=True):
    ts_now = get_mil_sec()
    # Active state
    AttributeKv.objects.update_or_create(
        entity=device,
        entity__tenant_id=device.tenant_id,
        attribute_type=AttributeKv.SERVER_SCOPE,
        attribute_key="active",
        defaults={"bool_v": connected, "entity_type": "DEVICE", "last_update_ts": ts_now},
    )
    # Last activity
    AttributeKv.objects.update_or_create(
        entity=device,
        entity__tenant_id=device.tenant_id,
        attribute_type=AttributeKv.SERVER_SCOPE,
        attribute_key="lastActivityTime",
        defaults={"long_v": ts_now, "entity_type": "DEVICE", "last_update_ts": ts_now},
    )


def _get_or_create_device(name, from_device):
    """Fetch or create a Device by exact name, preserving case-insensitive lookup."""
    # Try case-insensitive lookup first
    sub = Device.objects.filter(
        name__iexact=name,
        tenant_id=from_device.tenant_id,
        is_active=True,
    ).first()
    if sub:
        return sub
    # Create new device with provided name
    obj = Device(
        name=name,
        tenant_id=from_device.tenant_id,
        is_active=True,
        type="default",
        device_profile_id=from_device.device_profile_id,
    )
    obj.full_clean()
    obj.save()
    # Initialize credentials
    DeviceCredentials.objects.create(
        credentials_type="ACCESS_TOKEN",
        credentials_id=get_random_letter(),
        device=obj,
    )
    # Create relation
    Relation.objects.update_or_create(
        to_id_id=obj.id,
        from_type="DEVICE",
        to_type="DEVICE",
        relation_type_group="COMMON",
        relation_type="Created",
        defaults={"from_id_id": from_device.id, "updated_at": get_mil_sec()},
    )
    return obj
