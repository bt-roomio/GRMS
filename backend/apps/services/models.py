import uuid
from typing import ClassVar, NamedTuple, cast

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q, UniqueConstraint

from services.mapping.constants import TAG_NAME_MAX_LENGTH, Direction, OnInvalid
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
    """An integrator's value format: ``MappingRule`` objects, each for one or more tag names, and
    ``composite_rules``, each making one integrator value of several tags.

    An integration uses a ``tenant`` profile through ``Integration.mapping_profile``. The
    ``room_type`` and ``device`` profiles of the same integrator in the tenant hold the rules that
    differ for their targets (``room_types`` or ``devices``, one or more); a tag takes its rule
    from the device profile, then the room type profile, then the integration's profile. A target
    belongs to one profile of the integrator in the tenant (``MappingProfileTarget``, see
    ``SCOPE_TARGETS``)."""

    class Scope(models.TextChoices):
        TENANT = "tenant", "Tenant"
        ROOM_TYPE = "room_type", "Room type"
        DEVICE = "device", "Device"

    name = models.CharField(max_length=255)
    integrator = models.ForeignKey(
        "services.Integrator", models.CASCADE, "mapping_profiles", to_field="name", db_column="integrator"
    )
    tenant = models.ForeignKey("main.Tenant", models.CASCADE, "mapping_profiles")
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.TENANT)
    room_types = models.ManyToManyField(
        "main.RoomType", "mapping_profiles", through="services.MappingProfileRoomType", blank=True
    )
    devices = models.ManyToManyField(
        "main.Device", "mapping_profiles", through="services.MappingProfileDevice", blank=True
    )
    composite_rules = models.JSONField(
        default=list,
        blank=True,
        help_text="Rules making one integrator value of several tags, see services.mapping.composite.",
    )

    objects: ClassVar[MappingProfileQuerySet] = cast(MappingProfileQuerySet, MappingProfileQuerySet.as_manager())

    def __str__(self):
        return str(self.name)

    class Meta(BaseModel.Meta):
        db_table = "services_mapping_profile"
        constraints: ClassVar[list] = [
            UniqueConstraint(fields=("name", "tenant"), name="unique_mapping_profile_name_tenant"),
        ]


class MappingProfileTarget(BaseModel):
    """A target of a ``room_type`` or ``device`` profile. ``tenant`` and ``integrator`` repeat the
    profile's only for the database to keep one profile per target and integrator in a tenant:
    the profile serializer keeps them in step, and readers go by the profile's own fields."""

    profile = models.ForeignKey("services.MappingProfile", models.CASCADE, "+")
    tenant = models.ForeignKey("main.Tenant", models.CASCADE, "+")
    integrator = models.ForeignKey("services.Integrator", models.CASCADE, "+", to_field="name", db_column="integrator")

    class Meta(BaseModel.Meta):
        abstract = True


class MappingProfileRoomType(MappingProfileTarget):
    room_type = models.ForeignKey("main.RoomType", models.CASCADE, "+")

    class Meta(MappingProfileTarget.Meta):
        db_table = "services_mapping_profile_room_type"
        constraints: ClassVar[list] = [
            UniqueConstraint(
                fields=("tenant", "integrator", "room_type"), name="unique_mapping_profile_integrator_room_type"
            ),
        ]


class MappingProfileDevice(MappingProfileTarget):
    device = models.ForeignKey("main.Device", models.CASCADE, "+")

    class Meta(MappingProfileTarget.Meta):
        db_table = "services_mapping_profile_device"
        constraints: ClassVar[list] = [
            UniqueConstraint(
                fields=("tenant", "integrator", "device"), name="unique_mapping_profile_integrator_device"
            ),
        ]


class ScopeTarget(NamedTuple):
    """How a scoped profile holds its targets."""

    field: str  # the profile's targets field
    link: type[MappingProfileTarget]
    key: str  # the link's target field
    label: str

    @property
    def constraint(self) -> str:
        """The name of the link's uniqueness constraint."""
        return f"unique_mapping_profile_integrator_{self.key}"


# The targets of each scoped profile; a tenant profile has none.
SCOPE_TARGETS: dict[str, ScopeTarget] = {
    MappingProfile.Scope.ROOM_TYPE: ScopeTarget("room_types", MappingProfileRoomType, "room_type", "Room type"),
    MappingProfile.Scope.DEVICE: ScopeTarget("devices", MappingProfileDevice, "device", "Device"),
}


class MappingRule(BaseModel):
    """One rule of a profile, see ``services.mapping.engine``. The rule converts every tag whose
    name (an attribute key or a telemetry key) is in ``tag_names``, wherever its profile applies.
    A tag name belongs to one rule of a profile: the serializer checks it, the database cannot."""

    profile = models.ForeignKey("services.MappingProfile", models.CASCADE, "rules")
    tag_names = ArrayField(models.CharField(max_length=TAG_NAME_MAX_LENGTH), default=list)
    external = models.JSONField(help_text='The integrator side, e.g. {"value_type": "integer"}.')
    direction = models.CharField(max_length=20, choices=Direction.choices, default=Direction.BOTH)
    transform = models.JSONField()
    on_invalid = models.CharField(max_length=20, choices=OnInvalid.choices, default=OnInvalid.REJECT)
    on_invalid_value = models.JSONField(
        null=True, blank=True, help_text="The GRMS value written instead of an invalid one under on_invalid const."
    )

    def __str__(self):
        return ", ".join(self.tag_names)

    def as_rule(self) -> dict:
        """The rule as the engine takes it."""
        return {
            "tag_names": list(self.tag_names),
            "external": self.external,
            "direction": self.direction,
            "transform": self.transform,
            "on_invalid": self.on_invalid,
            "on_invalid_value": self.on_invalid_value,
        }

    class Meta(BaseModel.Meta):
        db_table = "services_mapping_rule"
        ordering = ("tag_names",)
        constraints: ClassVar[list] = [
            # A rule without tag names would match no tag.
            models.CheckConstraint(check=Q(tag_names__len__gt=0), name="mapping_rule_tag_names_not_empty"),
        ]
