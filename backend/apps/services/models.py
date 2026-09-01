import uuid
from typing import ClassVar

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


class Integrator(BaseModel):
    id = None
    name = models.CharField(max_length=20, primary_key=True)
    client_id = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)


class Integration(BaseModel):
    integrator = models.ForeignKey("services.Integrator", models.CASCADE, to_field="name", db_column="integrator")
    description = models.TextField(null=True, blank=True)
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

    def __str__(self):
        return f"{self.integrator} ({self.tenant})"

    class Meta(BaseModel.Meta):
        db_table = "services_integration"
        constraints: ClassVar[list] = [
            UniqueConstraint(
                "integrator",
                "tenant",
                condition=Q(is_active=True),
                name="unique_integration_integrator_tenant_is_active",
            ),
        ]
