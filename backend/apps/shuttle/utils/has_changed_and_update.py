import json

from core.utils.redis_pool import sync_redis as redis_client


def has_changed_and_update(device_id: str, updates: list[dict], is_attribute_kv: bool = False) -> list[dict]:
    """
    Checks whether the data for the device has changed.
    Returns only the updates that actually changed.

    Args:
        device_id (int): Device ID
        updates (list[dict]): List of updates
        is_attribute_kv (bool): Flag indicating the cache type (attribute_kv or regular)

    Returns:
        list[dict]: List of updates that actually changed
    """
    # Determine the Redis key type
    key = f"device_cache:attribute_kv:{device_id}" if is_attribute_kv else f"device_cache:{device_id}"
    cached_raw = redis_client.get(key)
    cached = json.loads(cached_raw) if cached_raw else {}  # pyright: ignore

    changed = []
    for update in updates:
        # Determine the key type for the update
        update_key = f"{update['entity']}:{update.get('key_name', update.get('key'))}"
        old_value = cached.get(update_key)
        new_value = update.get("bool_v") or update.get("str_v") or update.get("dbl_v") or update.get("long_v")

        if update.get("key", "").endswith("_LOGS") or old_value != new_value:
            changed.append(update)
            cached[update_key] = new_value

    # Update the cache in Redis
    if changed:
        redis_client.set(key, json.dumps(cached), ex=3600)

    return changed


def has_changed_attrs(device_id: str, updates: list[dict]) -> list[dict]:
    key = f"attribute_kv:{device_id}"
    cached_raw = redis_client.get(key)
    cached = json.loads(cached_raw) if cached_raw else {}  # pyright: ignore

    changed = []
    for update in updates:
        update_key = f"{update.get('scope')}:{update.get('key_name')}"
        old_value = cached.get(update_key)
        new_value = update.get("value")

        if update.get("key", "").endswith("_LOGS") or old_value is not new_value:
            changed.append(update)
            cached[update_key] = new_value

    if changed:
        redis_client.set(key, json.dumps(cached), ex=3600)

    return changed


def get_cached_attributes(
    device_id: str, attribute_keys: list[str], attribute_type: str = "SERVER_SCOPE"
) -> dict | None:
    """
    Get attributes from the Redis cache.

    Args:
        device_id: Device UUID
        attribute_keys: List of attribute keys (e.g., ["active", "lastActivityTime"])
        attribute_type: Attribute type (SERVER_SCOPE, CLIENT_SCOPE, SHARED_SCOPE)

    Returns:
        dict with attributes, or None if the cache is empty
        Format: {
            "active": {"bool_v": True, "last_update_ts": 123, ...},
            "lastActivityTime": {"long_v": 123, ...}
        }
    """
    cache_key = f"device_attrs:{device_id}:{attribute_type}"
    cached_raw = redis_client.get(cache_key)

    if not cached_raw:
        return None

    try:
        cached_data = json.loads(cached_raw)
        # Check that all requested keys are in the cache
        if all(key in cached_data for key in attribute_keys):
            return cached_data
    except (json.JSONDecodeError, TypeError):
        return None

    return None


def get_cached_attributes_batch(
    device_ids: list[str], attribute_keys: list[str], attribute_type: str = "SERVER_SCOPE"
) -> dict[str, dict | None]:
    """Batch variant of :func:`get_cached_attributes` using a single Redis MGET.

    Returns ``{device_id: cached_data_or_None}`` for every id. Per-device semantics
    match the single version: a device is a hit only if all ``attribute_keys`` are
    present in its cached payload.
    """
    if not device_ids:
        return {}

    cache_keys = [f"device_attrs:{device_id}:{attribute_type}" for device_id in device_ids]
    raws = redis_client.mget(cache_keys)

    result: dict[str, dict | None] = {}
    for device_id, cached_raw in zip(device_ids, raws):
        if not cached_raw:
            result[device_id] = None
            continue
        try:
            cached_data = json.loads(cached_raw)
            result[device_id] = cached_data if all(key in cached_data for key in attribute_keys) else None
        except (json.JSONDecodeError, TypeError):
            result[device_id] = None
    return result


def set_cached_attributes(device_id: str, attributes_data: dict, attribute_type: str = "SERVER_SCOPE", ttl: int = 5):
    """
    Save attributes to the Redis cache.

    Args:
        device_id: Device UUID
        attributes_data: dict with attributes
        attribute_type: Attribute type
        ttl: Time-to-live in seconds (default: 5)
    """
    cache_key = f"device_attrs:{device_id}:{attribute_type}"
    redis_client.set(cache_key, json.dumps(attributes_data, default=str), ex=ttl)


def invalidate_attributes_cache(device_id: str, attribute_type: str = "SERVER_SCOPE"):
    """
    Delete the device attribute cache.

    Args:
        device_id: Device UUID
        attribute_type: Attribute type
    """
    cache_key = f"device_attrs:{device_id}:{attribute_type}"
    redis_client.delete(cache_key)
