import json

import redis
from django.conf import settings
from django.core.management.base import BaseCommand

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        has_changed_and_update()


def has_changed_and_update():
    key = "asgi:group:attribute_kv_updates"
    # members = redis_client.zrange(key, 0, -1)
    # or, if you also want the timestamp scores:
    members_with_scores = redis_client.zrange(key, 0, -1, withscores=True)

    print("Subscribers:", members_with_scores)

    # cached_raw = redis_client.get(key)
    # cached = json.loads(cached_raw) if cached_raw else {}  # pyright: ignore
    # print(cached)
