"""Shared Redis clients reused across the app.

Historically every module built its own ``redis.Redis(...)`` at import time, so a
single process opened several independent connection pools to the same server.
This module exposes one sync and one async client (each backed by redis-py's
internal connection pool, which is safe to share across threads / the event loop)
so callers reuse connections and batched pipelines/MGETs have a single home.
"""

import redis
import redis.asyncio as aioredis
from django.conf import settings

sync_redis: redis.Redis = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
async_redis: aioredis.Redis = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
