from typing import Any, ClassVar

from drf_yasg import openapi
from rest_framework import serializers

from core.utils.brute_force import get_lock_status, locked_emails, normalize_email
from core.utils.serializers import ValidatorSerializer
from main.models import Dashboard
from main.serializers.dashboard import SimpleDashboardSerializer
from users.models import Role, User
from users.serializers.role import RoleSimpleSerializer
from users.utils.tenant_access import available_tenants_qs, is_unscoped_superuser


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


class UserListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        # Lock status of the whole page in one batch instead of per user in the child
        users = list(data.all() if hasattr(data, "all") else data)
        self.context["locked_emails"] = locked_emails(user.email for user in users)
        return super().to_representation(users)


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.PrimaryKeyRelatedField(many=True, queryset=Role.objects.all(), required=True)
    dashboards = serializers.PrimaryKeyRelatedField(many=True, queryset=Dashboard.objects.all(), required=False)
    additional_info = serializers.JSONField(required=False, help_text="{excluded_fields: ['phone', 'email']}")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_at"] = instance.date_joined
        # A chain admin administers hotels without living in one, so `tenant` may be null.
        data["tenant_name"] = instance.tenant.title if instance.tenant_id else None
        data["dashboards"] = SimpleDashboardSerializer(instance.dashboards.all(), many=True).data
        locked = self.context.get("locked_emails")
        if locked is None:
            data["is_blocked"] = get_lock_status(instance.email)["is_locked"]
        else:
            data["is_blocked"] = normalize_email(instance.email) in locked
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

    def validate_tenant(self, value):
        """
        Move a user only into a hotel the caller may work with.

        Without this a hotel admin could push their own staff into any hotel of the system,
        and a chain admin out of their chain. Taking a user out of every hotel makes them
        a system-wide account, which only an unscoped superuser may create.
        """
        request = self.context.get("request")
        if request is None or is_unscoped_superuser(request.user):
            return value
        if value is None:
            raise serializers.ValidationError("Only an unscoped superuser can leave a user without a tenant.")
        if not available_tenants_qs(request.user).filter(pk=value.pk).exists():
            raise serializers.ValidationError("Tenant out of scope.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get("tenant_group"):
            target_is_superuser = self.instance.is_superuser if self.instance else False
            if not target_is_superuser:
                raise serializers.ValidationError({"tenant_group": "Only a superuser can administer a hotel chain."})

        # Checked here rather than in field validators: a PUT may move the user to another
        # hotel, and roles/dashboards must match the hotel the user ends up in.
        tenant_id = self._target_tenant_id(attrs)
        errors = {}
        if (roles_error := self._roles_error(attrs.get("roles"), tenant_id)) is not None:
            errors["roles"] = [roles_error]
        if (dashboards_error := self._dashboards_error(attrs.get("dashboards"), tenant_id)) is not None:
            errors["dashboards"] = [dashboards_error]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def _target_tenant_id(self, attrs):
        """The hotel the user belongs to once this request is saved."""
        if self.instance:
            if "tenant" in attrs:
                return attrs["tenant"].pk if attrs["tenant"] else None
            return self.instance.tenant_id
        # On create the views save the hotel themselves: the admin endpoint takes it from the
        # URL and passes it through the context, the tenant-facing one uses the caller's.
        tenant_id = self.context.get("tenant_id")
        request = self.context.get("request")
        if tenant_id is None and request is not None:
            tenant_id = request.user.tenant_id
        return tenant_id

    def _roles_error(self, roles, tenant_id):
        """
        Keep role assignment inside the hotel the account belongs to.

        The scope follows the *target* user, not the caller: the admin endpoints run
        as superuser, so keying off the caller let an admin borrow hotel A's role for
        an account in hotel B — which is exactly how permissions drift.
        """
        if not roles or self.context.get("request") is None:
            return None
        outsiders = [role.name for role in roles if role.tenant_id and str(role.tenant_id) != str(tenant_id)]
        if outsiders:
            return f"Role out of scope: {', '.join(outsiders)}."
        return None

    @staticmethod
    def _dashboards_error(dashboards, tenant_id):
        """Dashboards must belong to the target user's hotel, whoever calls the serializer."""
        if not dashboards:
            return None
        # A chain admin lives in no hotel, and `my_dashboards` only shows dashboards of the user's own one.
        if tenant_id is None:
            return "A user without a tenant cannot hold dashboards."
        outsiders = [d.title for d in dashboards if str(d.tenant_id) != str(tenant_id)]
        if outsiders:
            return f"Dashboard out of scope: {', '.join(outsiders)}."
        return None

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
        dashboards_data = validated_data.pop("dashboards", [])
        user = User.objects.create(**validated_data)
        user.roles.set(roles_data)
        user.dashboards.set(dashboards_data)
        return user

    def update(self, instance, validated_data):
        tenant_changed = "tenant" in validated_data and (
            (validated_data["tenant"].pk if validated_data["tenant"] else None) != instance.tenant_id
        )
        if tenant_changed and "dashboards" not in validated_data:
            # Dashboards of the old hotel would linger on the card and fail the next PUT that echoes them back.
            validated_data["dashboards"] = []
        instance = super().update(instance, validated_data)
        if tenant_changed:
            instance.dashboard_positions.all().delete()
        return instance

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
            "dashboards",
            "is_active",
        )
        extra_kwargs: ClassVar[dict[str, dict[str, bool]]] = {"is_superuser": {"read_only": True}}
        list_serializer_class = UserListSerializer


class UserDetailSerializer(serializers.ModelSerializer):
    def to_representation(self, instance: User):
        data = super().to_representation(instance)
        data["roles"] = RoleSimpleSerializer(instance.roles, many=True).data
        # A chain admin administers hotels without living in one, so `tenant` may be null.
        data["tenant_name"] = instance.tenant.title if instance.tenant_id else None
        data["dashboards"] = SimpleDashboardSerializer(instance.dashboards.all(), many=True).data
        data["is_blocked"] = get_lock_status(instance.email)["is_locked"]
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
            "dashboards",
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
