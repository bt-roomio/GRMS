import json

import redis
from django.conf import settings

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)


def has_changed_and_update(device_id: str, updates: list[dict], is_attribute_kv: bool = False) -> list[dict]:
    """
    Проверяет, изменились ли данные для устройства.
    Возвращает только те обновления, которые действительно изменились.

    Args:
        device_id (int): ID устройства
        updates (list[dict]): Список обновлений
        is_attribute_kv (bool): Флаг, указывающий тип кэша (attribute_kv или обычный)

    Returns:
        list[dict]: Список обновлений, которые действительно изменились
    """
    # Определяем тип ключа для Redis
    key = f"device_cache:attribute_kv:{device_id}" if is_attribute_kv else f"device_cache:{device_id}"
    cached_raw = redis_client.get(key)
    cached = json.loads(cached_raw) if cached_raw else {}  # pyright: ignore

    changed = []
    for update in updates:
        # Определяем тип ключа для обновления
        update_key = f"{update['entity']}:{update.get('key_name', update.get('key'))}"
        old_value = cached.get(update_key)
        new_value = update.get("bool_v") or update.get("str_v") or update.get("dbl_v") or update.get("long_v")

        if update.get("key", "").endswith("_LOGS") or old_value != new_value:
            changed.append(update)
            cached[update_key] = new_value

    # Обновляем кэш в Redis
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
    Получить атрибуты из Redis кеша.

    Args:
        device_id: UUID устройства
        attribute_keys: Список ключей атрибутов (e.g., ["active", "lastActivityTime"])
        attribute_type: Тип атрибута (SERVER_SCOPE, CLIENT_SCOPE, SHARED_SCOPE)

    Returns:
        dict с атрибутами или None если кеш пуст
        Формат: {
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
        # Проверить, что все запрошенные ключи есть в кеше
        if all(key in cached_data for key in attribute_keys):
            return cached_data
    except (json.JSONDecodeError, TypeError):
        return None

    return None


def set_cached_attributes(device_id: str, attributes_data: dict, attribute_type: str = "SERVER_SCOPE", ttl: int = 5):
    """
    Сохранить атрибуты в Redis кеш.

    Args:
        device_id: UUID устройства
        attributes_data: dict с атрибутами
        attribute_type: Тип атрибута
        ttl: Time-to-live в секундах (default: 5)
    """
    cache_key = f"device_attrs:{device_id}:{attribute_type}"
    redis_client.set(cache_key, json.dumps(attributes_data, default=str), ex=ttl)


def invalidate_attributes_cache(device_id: str, attribute_type: str = "SERVER_SCOPE"):
    """
    Удалить кеш атрибутов устройства.

    Args:
        device_id: UUID устройства
        attribute_type: Тип атрибута
    """
    cache_key = f"device_attrs:{device_id}:{attribute_type}"
    redis_client.delete(cache_key)
