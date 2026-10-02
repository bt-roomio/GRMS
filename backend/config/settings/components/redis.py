import os
from typing import Any

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")


def _redis_cache(db: int, key_prefix: str, timeout: int, max_connections: int, **options: Any) -> dict[str, Any]:
    return {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{db}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": max_connections,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            **options,
        },
        "KEY_PREFIX": key_prefix,
        "TIMEOUT": timeout,
    }


CACHES = {
    "default": _redis_cache(
        4,
        "grms",
        timeout=300,
        max_connections=100,
        COMPRESSOR="django_redis.compressors.zlib.ZlibCompressor",
    ),
    "security": _redis_cache(2, "grms_security", timeout=900, max_connections=50),
    "http": _redis_cache(3, "grms_http", timeout=900, max_connections=50),
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
            "serializer_format": "uuidjson",
            "capacity": 5000,
            "expiry": 30,
            "group_expiry": 86400,
            "channel_capacity": {
                "http.request": 200,
                "websocket.send*": 100,
            },
        },
    },
}
