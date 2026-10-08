from channels_redis.serializers import registry
from django.apps import AppConfig

from core.serializers.channels_redis import UUIDSafeJSONSerializer


class CoreConfig(AppConfig):
    name = "core"

    def ready(self):
        registry.register_serializer("uuidjson", UUIDSafeJSONSerializer)
        import core.signals  # noqa  # pyright: ignore

        # Celery signal receivers for log context / logging setup. Connected here
        # rather than in config/celery.py, which is imported before apps/ is on
        # sys.path; worker and beat run django.setup() before configuring logging.
        import core.log.celery  # noqa  # pyright: ignore
