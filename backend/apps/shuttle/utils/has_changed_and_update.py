import json

import redis
from django.conf import settings

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)


def has_changed_and_update(device_id: int, updates: list[dict]) -> list[dict]:
    """
    Проверяет, изменились ли данные для устройства.
    Возвращает только те обновления, которые действительно изменились.
    """
    key = f"device_cache:{device_id}"
    cached_raw = redis_client.get(key)
    cached = json.loads(cached_raw) if cached_raw else {}  # pyright: ignore

    changed = []
    for update in updates:
        update_key = f"{update['entity']}:{update['key']}"
        old_value = cached.get(update_key)
        new_value = update.get("bool_v") or update.get("str_v") or update.get("dbl_v") or update.get("long_v")

        if old_value != new_value:
            changed.append(update)
            cached[update_key] = new_value

    # Обновляем кэш в Redis
    if changed:
        redis_client.set(key, json.dumps(cached))

    return changed
