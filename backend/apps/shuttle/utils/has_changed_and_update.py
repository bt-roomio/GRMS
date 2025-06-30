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
        redis_client.set(key, json.dumps(cached))

    return changed
