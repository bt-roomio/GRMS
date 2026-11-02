"""
The key catalogue behind the rule builder.

Only keys the tenant's devices have actually reported are offered: a dropdown
built from the global dictionary would list keys from other installations and
invite rules that can never match.
"""

from django.core.cache import caches

from main.models import Device
from shuttle.models import AttributeKv, TsKvDictionary, TsKvLatest

CACHE_TIMEOUT = 300


def cache_key(tenant_id) -> str:
    return f"alarms:available-keys:{tenant_id}"


def available_keys(tenant_id) -> dict[str, list[str]]:
    cache = caches["default"]
    key = cache_key(tenant_id)

    cached = cache.get(key)
    if cached is not None:
        return cached

    device_ids = Device.objects.filter(tenant_id=tenant_id, is_active=True).values_list("id", flat=True)

    key_ids = TsKvLatest.objects.filter(entity_id__in=device_ids).values_list("key_id", flat=True).distinct()
    timeseries = sorted(TsKvDictionary.objects.filter(key_id__in=key_ids).values_list("key", flat=True).distinct())

    attributes = sorted(
        AttributeKv.objects.filter(entity_id__in=device_ids, attribute_type=AttributeKv.SERVER_SCOPE)
        .values_list("attribute_key", flat=True)
        .order_by()
        .distinct()
    )

    keys = {"timeseries": timeseries, "attributes": attributes}
    cache.set(key, keys, CACHE_TIMEOUT)
    return keys


def invalidate(tenant_id) -> None:
    caches["default"].delete(cache_key(tenant_id))
