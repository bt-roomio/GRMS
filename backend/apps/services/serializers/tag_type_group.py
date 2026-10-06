from dataclasses import dataclass

from django.db import IntegrityError

from rest_framework import serializers

from core.serializers.pagination import PaginationParams, PaginationSerializer
from services.models import TagTypeGroup


class TenantUniqueNameSerializer(serializers.ModelSerializer):
    """Base for write serializers of models unique on (name, tenant). The tenant is not a
    serializer field (the view passes it to save()), so DRF does not derive this validator
    from the constraint — it is checked here against ``context["tenant_id"]``."""

    unique_name_message = "An object with this name already exists."
    unique_name_constraint = ""  # the model's (name, tenant) UniqueConstraint name

    def save(self, **kwargs):
        # validate_name() runs before the insert, so a concurrent request with the same name can
        # still win the race; turn that constraint violation into the same 400, not a 500.
        try:
            return super().save(**kwargs)
        except IntegrityError as exc:
            constraint = getattr(getattr(exc.__cause__, "diag", None), "constraint_name", None)
            if constraint != self.unique_name_constraint:
                raise
            raise serializers.ValidationError({"name": [self.unique_name_message]}) from exc

    def validate_name(self, value):
        tenant_id = self.instance.tenant_id if self.instance else self.context["tenant_id"]
        duplicates = self.Meta.model.objects.filter(name=value, tenant_id=tenant_id)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(self.unique_name_message)
        return value


class TagTypeGroupShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagTypeGroup
        fields = ("id", "name")


class TagTypeGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagTypeGroup
        fields = ("id", "name", "tenant", "created_at", "updated_at")


class TagTypeGroupWriteSerializer(TenantUniqueNameSerializer):
    unique_name_message = "A tag type group with this name already exists."
    unique_name_constraint = "unique_tag_type_group_name_tenant"

    class Meta:
        model = TagTypeGroup
        fields = ("name",)


@dataclass
class TagTypeGroupFilterParams(PaginationParams):
    search: str | None
    sort_by: str


class TagTypeGroupFilterSerializer(PaginationSerializer[TagTypeGroupFilterParams]):
    SORT_CHOICES = ("name", "-name", "created_at", "-created_at")
    params_class = TagTypeGroupFilterParams

    search = serializers.CharField(
        default=None, allow_blank=True, help_text="Filter by name (case-insensitive substring)."
    )
    sort_by = serializers.ChoiceField(choices=SORT_CHOICES, default="name")
