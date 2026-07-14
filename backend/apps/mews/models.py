from django.db import models

from core.models import BaseModel, UpdateByModel


class MewsConfiguration(BaseModel, UpdateByModel):
    """
    Mews API configuration for each tenant
    Stores credentials and settings for Mews integration
    """

    tenant = models.OneToOneField(
        "main.Tenant", on_delete=models.CASCADE, related_name="mews_config", verbose_name="Tenant"
    )
    client_token = models.CharField(max_length=255, help_text="Mews ClientToken (application identifier)")
    access_token = models.CharField(max_length=255, help_text="Mews AccessToken (property-specific)")
    company_id = models.UUIDField(help_text="Mews Company ID")
    environment = models.CharField(
        max_length=20,
        choices=[
            ("demo", "Demo"),
            ("production", "Production"),
        ],
        default="production",
        help_text="Mews environment",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Enable/disable Mews integration for this tenant",  # pyright: ignore
    )
    auto_sync = models.BooleanField(
        default=True,
        help_text="Automatically sync reservations in real-time",  # pyright: ignore
    )
    last_sync = models.DateTimeField(null=True, blank=True, help_text="Last successful sync timestamp")

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table = "mews_configuration"
        verbose_name = "Mews Configuration"
        verbose_name_plural = "Mews Configurations"

    def __str__(self):
        return f"Mews Config for {self.tenant.title}"

    @property
    def api_base_url(self) -> str:
        """Get API base URL based on environment"""
        return {
            "demo": "https://api.mews-demo.com/api/connector/v1",
            "production": "https://api.mews.com/api/connector/v1",
        }.get(str(self.environment)) or "https://api.mews-demo.com/api/connector/v1"

    @property
    def ws_url(self):
        """Get WebSocket URL based on environment"""
        return {
            "demo": "wss://ws.mews-demo.com/ws/connector",
            "production": "wss://ws.mews.com/ws/connector",
        }.get(str(self.environment))
