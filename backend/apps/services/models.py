import uuid
from typing import ClassVar, cast

from django.db import models
from django.db.models import Q, UniqueConstraint

from services.querysets.integration import IntegrationQuerySet
from services.querysets.tag import TagTypeGroupQuerySet, TagTypeQuerySet


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


class TagTypeGroup(BaseModel):
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", models.CASCADE, "tag_type_groups", null=True, blank=True)

    objects: ClassVar[TagTypeGroupQuerySet] = cast(TagTypeGroupQuerySet, TagTypeGroupQuerySet.as_manager())

    def __str__(self):
        return str(self.name)

    class Meta(BaseModel.Meta):
        db_table = "services_tag_type_group"
        constraints: ClassVar[list] = [
            UniqueConstraint(fields=("name", "tenant"), nulls_distinct=False, name="unique_tag_type_group_name_tenant"),
        ]


class TagType(BaseModel):
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey(
        "main.Tenant",
        models.CASCADE,
        "tag_types",
        null=True,
        blank=True,
        help_text="Empty for a type shared by all tenants.",
    )
    group = models.ForeignKey("services.TagTypeGroup", models.PROTECT, "tag_types")

    objects: ClassVar[TagTypeQuerySet] = cast(TagTypeQuerySet, TagTypeQuerySet.as_manager())

    def __str__(self):
        return str(self.name)

    class Meta(BaseModel.Meta):
        db_table = "services_tag_type"
        constraints: ClassVar[list] = [
            # nulls_distinct=False: shared types (tenant is NULL) must have unique names too.
            UniqueConstraint(fields=("name", "tenant"), nulls_distinct=False, name="unique_tag_type_name_tenant"),
        ]


class TagRange(BaseModel):
    tag_type = models.ForeignKey("services.TagType", models.CASCADE, "tag_ranges")
    range_value = models.JSONField(
        null=True, blank=True, help_text='Range definition as JSON, e.g. {"min": 16, "max": 30}.'
    )

    def __str__(self):
        return str(self.range_value)

    class Meta(BaseModel.Meta):
        db_table = "services_tag_range"
