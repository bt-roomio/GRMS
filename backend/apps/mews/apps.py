from django.apps import AppConfig


class MewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mews"
    verbose_name = "Mews Integration"

    def ready(self):
        import mews.signals  # noqa # pyright: ignore
