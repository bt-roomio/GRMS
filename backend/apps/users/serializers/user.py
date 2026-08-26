from typing import Any, ClassVar

from drf_yasg import openapi
from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from users.models import Role, User
from users.serializers.role import RoleSimpleSerializer


class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email")


class AdditionalInfoField(serializers.JSONField):
    class Meta:
        swagger_schema_fields: ClassVar[dict[str, Any]] = {
            "type": openapi.TYPE_OBJECT,
            "title": "additional_info",
            "properties": {
                "excluded_fields": openapi.Schema(
                    title="additional_info",
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                ),
            },
        }


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.PrimaryKeyRelatedField(many=True, queryset=Role.objects.all(), required=True)
    additional_info = serializers.JSONField(required=False, help_text="{excluded_fields: ['phone', 'email']}")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_at"] = instance.date_joined
        # A chain admin administers hotels without living in one, so `tenant` may be null.
        data["tenant_name"] = instance.tenant.title if instance.tenant_id else None
        data["tenant_has_access_ai"] = instance.tenant.has_access_ai if instance.tenant_id else False
        return data

    def validate_tenant_group(self, value):
        """
        Pinning a user to a chain is a system-wide act.

        The serializer is shared with the tenant-facing endpoint, so the guard lives
        here rather than in a view: only a superuser who is not himself pinned may
        hand out (or revoke) chain administration.
        """
        request = self.context.get("request")
        if request is None:
            return value
        if not request.user.is_superuser or request.user.tenant_group_id:
            raise serializers.ValidationError("Only an unscoped superuser can assign a hotel chain.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get("tenant_group"):
            target_is_superuser = self.instance.is_superuser if self.instance else False
            if not target_is_superuser:
                raise serializers.ValidationError({"tenant_group": "Only a superuser can administer a hotel chain."})
        return attrs

    def validate_roles(self, value):
        """
        Keep role assignment inside the hotel the account belongs to.

        The scope follows the *target* user, not the caller: the admin endpoints run
        as superuser, so keying off the caller let an admin borrow hotel A's role for
        an account in hotel B — which is exactly how permissions drift.
        """
        request = self.context.get("request")
        if request is None:
            return value

        # On create the hotel is not in the payload — the admin endpoint takes it from the
        # URL and passes it through the context; the tenant-facing one falls back to the caller.
        target_tenant_id = self.instance.tenant_id if self.instance else self.context.get("tenant_id")
        if target_tenant_id is None:
            target_tenant_id = request.user.tenant_id
        outsiders = [role.name for role in value if role.tenant_id and role.tenant_id != target_tenant_id]
        if outsiders:
            raise serializers.ValidationError(f"Role out of scope: {', '.join(outsiders)}.")

        return value

    def validate_email(self, value):
        normalized_email = value.lower()

        user = User.objects.filter(email__iexact=normalized_email, is_active=True)
        if self.instance:
            if user.exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("User with this email already exists!")
        else:
            if user.exists():
                raise serializers.ValidationError("User with this email already exists!")

        return normalized_email

    def create(self, validated_data):
        roles_data = validated_data.pop("roles") if "roles" in validated_data else []
        user = User.objects.create(**validated_data)
        user.roles.set(roles_data)
        return user

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "is_superuser",
            "email",
            "additional_info",
            "phone",
            "date_joined",
            "tenant",
            "tenant_group",
            "roles",
            "is_active",
        )
        extra_kwargs: ClassVar[dict[str, dict[str, bool]]] = {"is_superuser": {"read_only": True}}


class UserDetailSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["roles"] = RoleSimpleSerializer(instance.roles, many=True).data
        # A chain admin administers hotels without living in one, so `tenant` may be null.
        data["tenant_name"] = instance.tenant.title if instance.tenant_id else None
        data["tenant_has_access_ai"] = instance.tenant.has_access_ai if instance.tenant_id else False
        return data

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "is_superuser",
            "additional_info",
            "phone",
            "date_joined",
            "tenant",
            "tenant_group",
            "roles",
            "is_active",
        )
        extra_kwargs: ClassVar[dict[str, dict[str, bool]]] = {
            "is_superuser": {"read_only": True},
            "tenant_group": {"read_only": True},
        }


class UserParams(ValidatorSerializer):
    SORT_FIELDS = ("first_name", "-first_name", "email", "-email")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    send_activation_mail = serializers.BooleanField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
    search_field = serializers.ChoiceField(choices=("first_name", "email", "phone"), required=False)
    search_value = serializers.CharField(required=False)
