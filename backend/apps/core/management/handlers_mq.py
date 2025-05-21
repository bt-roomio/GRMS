import json
import logging

from celery.exceptions import Reject
from django.conf import settings
from django.db import transaction

from core.management.handle_fias import handle_fias
from core.rabbitmq.config import send_to_rabbitmq
from core.utils.date import unix_to_datetime
from core.utils.get_time import get_mil_sec
from core.utils.random_letter import get_random_letter
from main.models import Device, DeviceCredentials
from shuttle.models import AttributeKv, Relation, RPCMessage, TsKv, TsKvDictionary, TsKvLatest
from shuttle.utils.find_compatible_field import find_compatible_field
from shuttle.utils.get_non_null_field import get_non_null_field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


def handlers_mq(ch, body):
    try:
        msg = json.loads(body)
        logger.debug("Received message: %s", msg)
        # Обработка устройства
        device_id = msg.get("sourceDeviceUUID")
        device = Device.objects.filter(id=device_id).first()
        if not device:
            logger.warning("Device not found: %s", device_id)
            return

        topic = msg.get("topic", "")
        data = msg.get("data")

        # Маршрутизация по теме
        if topic.startswith("v1/gateway/attributes/request") or topic.startswith("v1/devices/me/attributes/request"):
            logger.debug("Scheduling attribute response task for device %s topic %s", device_id, topic)
            handle_attribute_request(ch, device.id, topic, data)  # pyright:ignore
        else:
            logger.debug("Routing message for topic %s", topic)
            _route_and_handle(device, topic, data)
    except Reject:
        logger.warning("Rejecting message without retry")
        raise
    except Exception as exc:
        logger.exception("Error in process_mq_message, retrying... %s", exc)
        raise
    finally:
        logger.debug("process_mq_message completed")


def _route_and_handle(device, topic, data):
    logger.debug("_route_and_handle: device=%s topic=%s", device.id, topic)
    if topic == "v1/gateway/rpc":
        _handle_rpc(data)
    elif topic in ("v1/gateway/connect", "v1/gateway/disconnect"):
        _handle_connect_disconnect(device, topic, data)
    elif topic.endswith("/attributes"):
        _sync_attributes(device, topic, data)
    elif topic.endswith("/telemetry"):
        _sync_telemetry(device, topic, data)
    else:
        logger.debug("Unhandled topic: %s", topic)


# Кеши
_tskv_dict_cache = {}
_device_dict_cache = {}
_sub_device_dict_cache = {}
_sub_device_dict_getcreate_cache = {}


def get_tskv_dict(key):
    if key not in _tskv_dict_cache:
        obj, _ = TsKvDictionary.objects.get_or_create(key=key)
        _tskv_dict_cache[key] = obj
    return _tskv_dict_cache[key]


def _get_or_create_device(name, from_device):
    sub = Device.objects.filter(name__iexact=name, tenant_id=from_device.tenant_id, is_active=True).first()
    if sub:
        return sub
    logger.debug("Creating sub-device %s for tenant %s", name, from_device.tenant_id)
    obj = Device(
        name=name,
        tenant_id=from_device.tenant_id,
        is_active=True,
        type="default",
        device_profile_id=from_device.device_profile_id,
    )
    obj.full_clean()
    obj.save()
    DeviceCredentials.objects.create(
        credentials_type="ACCESS_TOKEN",
        credentials_id=get_random_letter(),
        device=obj,
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


def _handle_rpc(data):
    logger.debug("Handling RPC: %s", data)
    RPCMessage.objects.filter(id=data.get("id"), received=False).update(
        received=True,
        additional_info=data.get("data"),
    )


def _handle_connect_disconnect(device, topic, data):
    logger.debug("Handling %s for device %s", topic, device.id)
    name = data.get("device")
    sub = _sub_device_dict_cache.get(f"{device.tenant_id}:{name}")
    if not sub:
        sub = _get_or_create_device(name, device)
        _sub_device_dict_cache[f"{device.tenant_id}:{name}"] = sub
    connected = topic.endswith("connect")
    _update_activity_device(sub, connected)


def _sync_attributes(device, topic, payload):
    logger.debug("Sync attributes: device=%s topic=%s", device.id, topic)
    if topic.startswith("v1/gateway/") and isinstance(payload, dict) and not topic.endswith("request"):
        for sub_name, attrs in payload.items():
            sub_dev = _sub_device_dict_getcreate_cache.get(f"{device.tenant_id}:{sub_name}")
            if not sub_dev:
                sub_dev = _get_or_create_device(sub_name, device)
                _sub_device_dict_getcreate_cache[f"{device.tenant_id}:{sub_name}"] = sub_dev
            _update_attribute_store(sub_dev, attrs)
    else:
        _update_attribute_store(device, payload)


def _update_attribute_store(device, data):
    """
    Bulk save attributes for the given device using bulk_create and bulk_update.
    """
    # Normalize entries list
    entries = data if isinstance(data, list) else [data]
    ts_now = get_mil_sec()
    # Collect (attribute_key, field, value) tuples
    updates = []
    for entry in entries:
        for key, (field, value) in find_compatible_field(entry).items():
            updates.append((key, field, value))
    if not updates:
        logger.debug("No attribute entries to save for device %s", device.id)
        _update_activity_device(device)
        return

    # Determine unique keys
    keys = list({u[0] for u in updates})
    # Fetch existing AttributeKv rows
    existing_qs = AttributeKv.objects.filter(
        entity=device,
        attribute_type=AttributeKv.CLIENT_SCOPE,
        attribute_key__in=keys,
    )
    existing_map = {obj.attribute_key: obj for obj in existing_qs}

    to_create = []
    to_update = []
    for key, field, value in updates:
        # Prepare default values
        base = {
            "bool_v": None,
            "str_v": None,
            "long_v": None,
            "dbl_v": None,
            "json_v": None,
            "entity_type": "DEVICE",
            "last_update_ts": ts_now,
        }
        base[field] = value
        if key in existing_map:
            inst = existing_map[key]
            for attr_name, attr_val in base.items():
                setattr(inst, attr_name, attr_val)
            to_update.append(inst)
        else:
            inst = AttributeKv(
                entity=device,
                attribute_type=AttributeKv.CLIENT_SCOPE,
                attribute_key=key,
                **base,
            )
            to_create.append(inst)

    # Bulk operations
    if to_create:
        AttributeKv.objects.bulk_create(to_create)
    if to_update:
        fields = ["bool_v", "str_v", "long_v", "dbl_v", "json_v", "last_update_ts", "entity_type"]
        AttributeKv.objects.bulk_update(to_update, fields)

    logger.debug(
        "Bulk attributes processed for device %s: created=%d updated=%d", device.id, len(to_create), len(to_update)
    )
    _update_activity_device(device)


def _sync_telemetry(device, topic, payload):
    logger.debug(
        "Sync telemetry: device=%s topic=%s entries=%s",
        device.id,
        topic,
        len(payload) if hasattr(payload, "__len__") else 1,
    )
    entries = []
    if isinstance(payload, dict) and "ts" in payload and "values" in payload:
        entries.append((payload["ts"], payload["values"]))
    elif isinstance(payload, list):
        entries.extend((d["ts"], d["values"]) for d in payload if "ts" in d and "values" in d)
    if not entries:
        return
    ts_now = get_mil_sec()
    historical = []
    latest = []
    for ts_ms, vals in entries:
        ts_dt = unix_to_datetime(ts_ms)
        for key, (field, value) in find_compatible_field(vals).items():
            dict_obj = get_tskv_dict(key)
            historical.append(TsKv(entity_id=device.id, key=dict_obj, ts=ts_dt, **{field: value}))
            latest.append(TsKvLatest(entity_id=device.id, key=dict_obj, ts=ts_now, **{field: value}))
            if key == "messageFromFIAS":
                handle_fias(value, device)
    # Bulk save
    TsKv.objects.bulk_create(historical, ignore_conflicts=True)
    # Upsert latest
    unique_latest = {obj.key_id: obj for obj in latest}
    existing = TsKvLatest.objects.filter(entity=device, key_id__in=unique_latest.keys())
    existing_map = {e.key_id: e for e in existing}
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

    # Emit signals on commit
    def emit_signals():
        from django.db.models.signals import post_save

        for inst in to_create:
            post_save.send(sender=TsKvLatest, instance=inst, created=True)
        for inst in to_update:
            post_save.send(
                sender=TsKvLatest,
                instance=inst,
                created=False,
                update_fields=["ts", "bool_v", "str_v", "long_v", "dbl_v", "json_v"],
            )

    transaction.on_commit(emit_signals)
    _update_activity_device(device)


_response_connection = None
_response_channel = None


def handle_attribute_request(ch, device_id: str, topic: str, data: dict):
    logger.debug("handle_attribute_request: device=%s topic=%s", device_id, topic)
    try:
        device = Device.objects.get(id=device_id)
        shared_keys = data.get("sharedKeys") or data.get("keys") or []
        keys = shared_keys.split(",") if isinstance(shared_keys, str) else shared_keys
        attrs = AttributeKv.objects.filter(attribute_type=AttributeKv.SHARED_SCOPE, entity=device.id)
        attrs = attrs.filter(attribute_key__in=keys) if keys else attrs
        response = {
            "targetDeviceUUID": str(device.id),
            "topic": topic.replace("request", "response"),
            "data": {a.attribute_key: get_non_null_field(a)[1] for a in attrs},
        }
        send_to_rabbitmq(ch, response, routing_key="fromGRMS")
        logger.debug("Attribute response sent for device %s", device_id)
    except Exception as exc:
        logger.exception("Failed to send attribute response: %s", exc)
        raise


def _update_activity_device(device, connected=True):
    ts_now = get_mil_sec()

    # Active state
    attrs = AttributeKv.objects.filter(
        entity=device, attribute_type=AttributeKv.SERVER_SCOPE, attribute_key="active"
    ).first()
    if attrs and attrs.last_update_ts < ts_now - 20000:  # 10 min threshold
        return

    if attrs:
        attrs.bool_v = connected
        attrs.last_update_ts = ts_now
        attrs.entity_type = "DEVICE"
        attrs.save()
    elif not attrs:
        AttributeKv.objects.create(
            entity=device,
            attribute_key="active",
            entity_type="DEVICE",
            attribute_type=AttributeKv.SERVER_SCOPE,
            bool_v=connected,
            last_update_ts=ts_now,
        )

    # Last activity
    attrs = AttributeKv.objects.filter(
        entity=device, attribute_type=AttributeKv.SERVER_SCOPE, attribute_key="lastActivityTime"
    ).first()
    if attrs:
        attrs.long_v = ts_now
        attrs.last_update_ts = ts_now
        attrs.entity_type = "DEVICE"
        attrs.save()
    elif not attrs:
        AttributeKv.objects.create(
            entity=device,
            attribute_key="lastActivityTime",
            entity_type="DEVICE",
            attribute_type=AttributeKv.SERVER_SCOPE,
            long_v=ts_now,
            last_update_ts=ts_now,
        )
