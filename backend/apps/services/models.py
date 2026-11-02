import uuid
from typing import ClassVar, cast

from django.db import models
from django.db.models import Q, UniqueConstraint

from services.mapping.constants import Direction, OnInvalid
from services.querysets.integration import IntegrationQuerySet
from services.querysets.mapping import MappingProfileQuerySet
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
    mapping_profile = models.ForeignKey(
        "services.MappingProfile",
        models.SET_NULL,
        "integrations",
        null=True,
        blank=True,
        help_text="Converts tag values to the integrator's format; empty to exchange GRMS values as they are.",
    )

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


class MappingProfile(BaseModel):
    """An integrator's value format: one ``MappingRule`` per tag name.

    An integration uses a ``tenant`` profile through ``Integration.mapping_profile``. The
    ``room_type`` and ``device`` profiles of the same integrator in the tenant hold the rules that
    differ for their target; a tag takes its rule from the device profile, then the room type
    profile, then the integration's profile."""

    class Scope(models.TextChoices):
        TENANT = "tenant", "Tenant"
        ROOM_TYPE = "room_type", "Room type"
        DEVICE = "device", "Device"

    # The target field of each scope; None for the tenant scope.
    TARGET_FIELDS: ClassVar[dict] = {
        Scope.TENANT: None,
        Scope.ROOM_TYPE: "room_type",
        Scope.DEVICE: "device",
    }

    name = models.CharField(max_length=255)
    integrator = models.ForeignKey(
        "services.Integrator", models.CASCADE, "mapping_profiles", to_field="name", db_column="integrator"
    )
    tenant = models.ForeignKey("main.Tenant", models.CASCADE, "mapping_profiles")
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.TENANT)
    room_type = models.ForeignKey("main.RoomType", models.CASCADE, "mapping_profiles", null=True, blank=True)
    device = models.ForeignKey("main.Device", models.CASCADE, "mapping_profiles", null=True, blank=True)

    objects: ClassVar[MappingProfileQuerySet] = cast(MappingProfileQuerySet, MappingProfileQuerySet.as_manager())

    def __str__(self):
        return str(self.name)

    class Meta(BaseModel.Meta):
        db_table = "services_mapping_profile"
        constraints: ClassVar[list] = [
            UniqueConstraint(fields=("name", "tenant"), name="unique_mapping_profile_name_tenant"),
            # Exactly the scope's own target is set; a tenant profile has none.
            models.CheckConstraint(
                check=(
                    Q(scope="tenant", room_type__isnull=True, device__isnull=True)
                    | Q(scope="room_type", room_type__isnull=False, device__isnull=True)
                    | Q(scope="device", room_type__isnull=True, device__isnull=False)
                ),
                name="mapping_profile_target_matches_scope",
            ),
            UniqueConstraint(
                fields=("tenant", "integrator", "room_type"),
                condition=Q(scope="room_type"),
                name="unique_mapping_profile_integrator_room_type",
            ),
            UniqueConstraint(
                fields=("tenant", "integrator", "device"),
                condition=Q(scope="device"),
                name="unique_mapping_profile_integrator_device",
            ),
        ]


class MappingRule(BaseModel):
    """One rule of a profile, see ``services.mapping.engine``. The rule converts every tag named
    ``tag_name`` (an attribute key or a telemetry key) its profile applies to."""

    profile = models.ForeignKey("services.MappingProfile", models.CASCADE, "rules")
    tag_name = models.CharField(max_length=255)
    external = models.JSONField(help_text='The integrator side, e.g. {"value_type": "integer"}.')
    direction = models.CharField(max_length=20, choices=Direction.choices, default=Direction.BOTH)
    transform = models.JSONField()
    on_invalid = models.CharField(max_length=20, choices=OnInvalid.choices, default=OnInvalid.REJECT)
    on_invalid_value = models.JSONField(
        null=True, blank=True, help_text="The GRMS value written instead of an invalid one under on_invalid const."
    )

    def __str__(self):
        return str(self.tag_name)

    def as_rule(self) -> dict:
        """The rule as the engine takes it."""
        return {
            "tag_name": self.tag_name,
            "external": self.external,
            "direction": self.direction,
            "transform": self.transform,
            "on_invalid": self.on_invalid,
            "on_invalid_value": self.on_invalid_value,
        }

    class Meta(BaseModel.Meta):
        db_table = "services_mapping_rule"
        ordering = ("tag_name",)
        constraints: ClassVar[list] = [
            UniqueConstraint(fields=("profile", "tag_name"), name="unique_mapping_rule_profile_tag_name"),
        ]
