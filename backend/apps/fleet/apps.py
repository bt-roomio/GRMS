from django.apps import AppConfig


class FleetConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fleet"
    verbose_name = "Fleet"

    def ready(self):
        import fleet.signals  # noqa  # pyright: ignore
