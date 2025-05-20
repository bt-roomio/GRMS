import asyncio
import json
import logging

import aio_pika
from celery import shared_task
from celery.exceptions import Reject
from django.conf import settings
from django.db import transaction

from core.management.handle_fias import handle_fias
from core.utils.date import unix_to_datetime
from core.utils.get_time import get_mil_sec
from core.utils.random_letter import get_random_letter
from main.models import Device, DeviceCredentials
from shuttle.models import AttributeKv, Relation, RPCMessage, TsKv, TsKvDictionary, TsKvLatest
from shuttle.utils.find_compatible_field import find_compatible_field
from shuttle.utils.get_non_null_field import get_non_null_field

# Настройка логирования для видимости в Celery-воркере
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


# Celery-конфигурация: основной таск process_mq_message получает до 20 сообщений в секунду
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 5},
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    rate_limit="20/s",
)
def process_mq_message(self, body_str: str):
    logger.debug("process_mq_message started")
    try:
        msg = json.loads(body_str)
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
            handle_attribute_request.delay(device.id, topic, data)  # pyright:ignore
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
    entries = data if isinstance(data, list) else [data]
    ts_now = get_mil_sec()
    with transaction.atomic():
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
        logger.debug("Attributes updated for device %s", device.id)
        _update_activity_gateway(device)


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
            historical.append(TsKv(entity=device, key=dict_obj, ts=ts_dt, **{field: value}))
            latest.append(TsKvLatest(entity=device, key=dict_obj, ts=ts_now, **{field: value}))
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
    _update_activity_gateway(device)


_response_connection = None
_response_channel = None


async def _get_response_channel():
    global _response_connection, _response_channel
    if _response_connection is None or _response_connection.is_closed:
        logger.debug("Opening new aio-pika connection for responses")
        _response_connection = await aio_pika.connect_robust(
            host=settings.RABBIT_HOST,
            port=settings.RABBIT_PORT,
            login=settings.RABBIT_LOGIN,
            password=settings.RABBIT_PASSWORD,
        )
        _response_channel = await _response_connection.channel()
    return _response_channel


async def send_to_rabbitmq_async(message: dict, routing_key: str):
    logger.debug("Sending async response to routing_key=%s message=%s", routing_key, message)
    channel = await _get_response_channel()
    exchange = await channel.get_exchange("toGRMS")  # pyright:ignore
    await exchange.publish(
        aio_pika.Message(body=json.dumps(message).encode()),
        routing_key=routing_key,
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 2},
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    rate_limit="10/s",
)
def handle_attribute_request(self, device_id: str, topic: str, data: dict):
    logger.debug("handle_attribute_request: device=%s topic=%s", device_id, topic)
    try:
        device = Device.objects.get(id=device_id)
        shared_keys = data.get("sharedKeys") or data.get("keys") or []
        keys = shared_keys.split(",") if isinstance(shared_keys, str) else shared_keys
        attrs = AttributeKv.objects.filter(
            attribute_type=AttributeKv.SHARED_SCOPE, entity=device.id, attribute_key__in=keys if keys else None
        )
        response = {
            "targetDeviceUUID": str(device.id),
            "topic": topic.replace("request", "response"),
            "data": {a.attribute_key: get_non_null_field(a)[1] for a in attrs},
        }
        asyncio.run(send_to_rabbitmq_async(response, routing_key=response["topic"]))
        logger.debug("Attribute response sent for device %s", device_id)
    except Exception as exc:
        logger.exception("Failed to send attribute response: %s", exc)
        raise


def _update_activity_gateway(device):
    if Device.objects.filter(id=device.id, tenant_id=device.tenant_id).exists():
        _update_activity_device(device)


def _update_activity_device(device, connected=True):
    ts_now = get_mil_sec()
    # Active state
    attrs = AttributeKv.objects.filter(
        entity=device, attribute_type=AttributeKv.SERVER_SCOPE, attribute_key="active"
    ).first()
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
