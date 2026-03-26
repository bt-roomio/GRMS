import logging
from typing import cast

from django.core.cache import caches
from django_redis.cache import RedisCache

logger = logging.getLogger(__name__)

QUICK_CACHE_PREFIX = "quick"


def invalidate_quick_cache(prefix: str, tenant_id) -> None:
    try:
        cast(RedisCache, caches["http"]).delete_pattern(f"{QUICK_CACHE_PREFIX}:{prefix}:{tenant_id}*")
    except Exception as e:
        logger.warning("Failed to invalidate cache for prefix=%s tenant=%s: %s", prefix, tenant_id, e)
