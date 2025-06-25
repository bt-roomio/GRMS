import json
import logging
from typing import TypedDict

import redis
from django.conf import settings

from core.utils.get_time import get_mil_sec
from core.utils.random_letter import get_random_letter
from core.utils.slugify import slugify_key
from main.models import Device, DeviceCredentials
from shuttle.models import Relation

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

EXPIRY_TIME = 60


class DeviceType(TypedDict):
    id: str
    name: str
    tenant_id: str
    device_profile_id: str


def get_device(device_id: str, tenant_id=None) -> DeviceType | None:
    logger.debug("Getting device: %s", device_id)
    cache_key = f"prs_msg:device_cache:{device_id}"
    cached_device_raw = redis_client.get(cache_key)
    cached_device = cached_device_raw.decode("utf-8") if isinstance(cached_device_raw, bytes) else None

    if cached_device:
        logger.debug("Device found in cache: %s", cached_device)
        return json.loads(cached_device)

    filters = {"id": device_id}
    if "&" in device_id:
        filters = {"name": device_id.split("&")[1], "tenant_id": tenant_id, "is_active": True}
    device = Device.objects.filter(**filters).first()

    if not device:
        return None
    data = _device_cache(cache_key, device)
    return data


def _device_cache(cache_key, device):
    data: DeviceType = {
        "id": str(device.id),
        "name": device.name,
        "tenant_id": str(device.tenant_id),
        "device_profile_id": str(device.device_profile_id),
    }
    redis_client.set(cache_key, json.dumps(data), ex=EXPIRY_TIME)
    logger.debug("Device cached: %s", device)
    return data


def get_sub_device(device: DeviceType, name: str):
    sub_cache_key = slugify_key(device.get("id") + "&" + name)
    sub_device = get_device(sub_cache_key, device.get("tenant_id"))

    if not sub_device:
        sub_device = get_or_create_device(name, device)
        cache_key = f"prs_msg:sub_device_cache:{sub_cache_key}"
        sub_device = _device_cache(cache_key, sub_device)

    return sub_device


def get_or_create_device(name, from_device):
    tenant_id = from_device.get("tenant_id")
    device_profile_id = from_device.get("device_profile_id")
    sub = Device.objects.filter(name__iexact=name, tenant_id=tenant_id, is_active=True).first()
    if sub:
        return sub
    logger.debug("Creating sub-device %s for tenant %s", name, tenant_id)
    obj = Device(
        name=name,
        tenant_id=tenant_id,
        is_active=True,
        type="default",
        device_profile_id=device_profile_id,
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
        defaults={"from_id_id": from_device.get("id"), "updated_at": get_mil_sec()},
    )
    return obj
