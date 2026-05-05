import uuid

from django.db import models
from django.db.models import Q, UniqueConstraint

from services.querysets.integration import IntegrationQuerySet


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False, null=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False, null=True)
    created_by = models.ForeignKey("users.User", models.SET_NULL, "created_%(model_name)ss", null=True, blank=True)
    updated_by = models.ForeignKey("users.User", models.SET_NULL, "updated_%(model_name)ss", null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ("id",)


class Integration(BaseModel):
    class Type(models.TextChoices):
        FIAS = "fias", "Fias"
        HOTEZA = "hoteza", "Hoteza"
        MEWS = "mews", "Mews"

    name = models.CharField(max_length=20, choices=Type.choices)
    description = models.TextField(default="", blank=True)
    hotel_id = models.CharField(max_length=100, null=True, blank=True)
    access_token = models.CharField(max_length=100, null=True, blank=True, help_text="For KeyCards")
    additional_info = models.JSONField(null=True, blank=True)
    enable = models.BooleanField("enable", default=False, help_text="Designates whether this integration is enable.")
    is_active = models.BooleanField(
        "active",
        default=True,
        help_text="Designates whether this user should be treated as active. "
        "Unselect this instead of deleting accounts.",
    )
    tenant = models.ForeignKey("main.Tenant", models.CASCADE, "integration")

    objects = IntegrationQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        db_table = "services_integration"
        constraints = [
            UniqueConstraint(
                "name",
                "tenant",
                condition=Q(is_active=True),
                name="unique_integration_name_tenant_is_active",
            ),
        ]
