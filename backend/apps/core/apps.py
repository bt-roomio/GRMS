from channels_redis.serializers import registry
from django.apps import AppConfig

from core.serializers.channels_redis import UUIDSafeJSONSerializer


class CoreConfig(AppConfig):
    name = "core"

    def ready(self):
        registry.register_serializer("uuidjson", UUIDSafeJSONSerializer)
        import core.signals  # noqa  # pyright: ignore
