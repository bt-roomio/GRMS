import logging

import orjson
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.management.mq.devices.device_cache import (
    _DEVICE_MEMORY_CACHE,
    _MEMORY_CACHE_TTL,
    DeviceType,
    _update_memory_cache,
    build_device_data,
    device_cache_key,
)
from core.utils.get_time import get_mil_sec
from core.utils.random_letter import get_random_letter
from core.utils.redis_pool import sync_redis as redis_client
from core.utils.slugify import slugify_key
from main.models import Device, DeviceCredentials, DeviceProfile
from shuttle.models import Relation

logger = logging.getLogger(__name__)

# Increased from 60s to 600s (10 minutes) - devices rarely change
EXPIRY_TIME = 600
RELATION_CACHE_TTL = 3600  # 1 hour
PROFILE_CACHE_TTL = 3600  # 1 hour - device profiles are stable

# Process-local cache for DeviceProfile ids keyed by "tenant_id:profile_name"
_PROFILE_MEMORY_CACHE: dict[str, dict] = {}


def get_device(device_id: str, tenant_id=None) -> DeviceType | None:
    """Get device with 2-tier caching: memory → Redis → database"""
    logger.debug("Getting device: %s", device_id)

    # Tier 1: Check in-memory cache (fastest, no network)
    current_time = get_mil_sec() // 1000  # seconds
    cache_entry = _DEVICE_MEMORY_CACHE.get(device_id)
    if cache_entry and (current_time - cache_entry["cached_at"]) < _MEMORY_CACHE_TTL:
        logger.debug("Device found in memory cache: %s", device_id)
        return cache_entry["data"]

    # Tier 2: Check Redis cache
    cache_key = device_cache_key(device_id)
    cached_device_raw = redis_client.get(cache_key)
    cached_device = cached_device_raw.decode("utf-8") if isinstance(cached_device_raw, bytes) else None

    if cached_device:
        logger.debug("Device found in Redis cache: %s", cached_device)
        data = orjson.loads(cached_device)
        # Populate memory cache from Redis hit
        _update_memory_cache(device_id, data)
        return data

    # Tier 3: Database lookup
    filters = {"id": device_id}
    if "&" in device_id:
        filters = {"name": device_id.split("&")[1], "tenant_id": tenant_id, "is_active": True}
    device = Device.objects.filter(**filters).first()

    if not device:
        return None

    data = _device_cache(cache_key, device)
    # Also cache in memory
    _update_memory_cache(device_id, data)
    return data


def _device_cache(cache_key, device):
    data = build_device_data(device.id, device.name, device.tenant_id, device.device_profile_id)
    redis_client.set(cache_key, orjson.dumps(data), ex=EXPIRY_TIME)
    logger.debug("Device cached: %s", device)
    return data


def _ensure_relation(from_id: str, to_id: str):
    """Ensure Relation gateway→sub-device exists; Redis-cached to avoid per-message DB hit."""
    cache_key = f"prs_msg:relation:{from_id}:{to_id}"
    if redis_client.exists(cache_key):
        return
    Relation.objects.get_or_create(
        from_id_id=from_id,
        to_id_id=to_id,
        from_type="DEVICE",
        to_type="DEVICE",
        relation_type_group="COMMON",
        relation_type="Created",
        defaults={"updated_at": get_mil_sec()},
    )
    redis_client.set(cache_key, "1", ex=RELATION_CACHE_TTL)


def _resolve_device_profile_id(tenant_id, profile_name: str) -> str:
    """Resolve a DeviceProfile id by (tenant_id, name) with memory → Redis → DB caching.

    Profiles are stable, so this avoids a DeviceProfile round-trip on every
    connect/disconnect that carries a device_type. Also replaces the risky
    get_or_create(name__iexact=...) (lookup doubling as a create field) with an
    explicit filter-then-create.
    """
    cache_id = f"{tenant_id}:{profile_name.lower()}"
    now = get_mil_sec() // 1000
    entry = _PROFILE_MEMORY_CACHE.get(cache_id)
    if entry and (now - entry["cached_at"]) < PROFILE_CACHE_TTL:
        return entry["id"]

    redis_key = f"prs_msg:device_profile:{cache_id}"
    cached_raw = redis_client.get(redis_key)
    if cached_raw:
        profile_id = cached_raw.decode("utf-8") if isinstance(cached_raw, bytes) else cached_raw
        _PROFILE_MEMORY_CACHE[cache_id] = {"id": profile_id, "cached_at": now}
        return profile_id

    profile = DeviceProfile.objects.filter(name__iexact=profile_name, tenant_id=tenant_id, active=True).first()
    if not profile:
        try:
            with transaction.atomic():
                profile = DeviceProfile.objects.create(
                    name=profile_name, tenant_id=tenant_id, active=True, type="DEFAULT"
                )
        except IntegrityError:
            # Параллельный поток/реплика создал профиль — берём существующий (unique_active_device_profile).
            profile = DeviceProfile.objects.filter(name__iexact=profile_name, tenant_id=tenant_id, active=True).first()
            if not profile:
                raise
    profile_id = str(profile.id)

    redis_client.set(redis_key, profile_id, ex=PROFILE_CACHE_TTL)
    _PROFILE_MEMORY_CACHE[cache_id] = {"id": profile_id, "cached_at": now}
    return profile_id


def get_sub_device(device: DeviceType, name: str, device_type: str | None = None):
    sub_cache_key = slugify_key(device.get("id") + "&" + name)  # "UUID_DEVICE & SUB_DEVICE"
    sub_device = get_device(sub_cache_key, device.get("tenant_id"))

    if device_type:
        name_map = {"ttlock": "TTLock", "fanvil_intercom": "Fanvil Intercom", "default": "Default"}
        dt = device_type.strip().lower().replace("-", "_")
        profile_name = name_map.get(dt) or " ".join(w.capitalize() for w in dt.split("_") if w)

        device["device_profile_id"] = _resolve_device_profile_id(device.get("tenant_id"), profile_name)

    if not sub_device:
        sub_device = get_or_create_device(name, device)
        cache_key = f"prs_msg:sub_device_cache:{sub_cache_key}"
        sub_device = _device_cache(cache_key, sub_device)

    _ensure_relation(device.get("id"), sub_device.get("id"))
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
    try:
        with transaction.atomic():
            obj.full_clean()
            obj.save()
            DeviceCredentials.objects.create(
                credentials_type="ACCESS_TOKEN",
                credentials_id=get_random_letter(),
                device=obj,
            )
    except (IntegrityError, ValidationError):
        # Параллельный поток/реплика создал устройство с тем же (name, tenant) —
        # берём существующее (unique_device_name_tenant_is_active) вместо падения батча.
        existing = Device.objects.filter(name__iexact=name, tenant_id=tenant_id, is_active=True).first()
        if existing:
            return existing
        raise
    Relation.objects.update_or_create(
        to_id_id=obj.id,
        from_type="DEVICE",
        to_type="DEVICE",
        relation_type_group="COMMON",
        relation_type="Created",
        defaults={"from_id_id": from_device.get("id"), "updated_at": get_mil_sec()},
    )
    return obj
