import re

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Dashboard
from users.models import Role, User


class SimpleDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = (
            "id",
            "title",
            "assigned_customers",
            "mobile_hide",
            "mobile_order",
            "image",
            "external_id",
        )


class MyDashboardSerializer(serializers.ModelSerializer):
    """A full dashboard as its holder opens it: no holders, so staff do not see who else has it."""

    class Meta:
        model = Dashboard
        fields = (
            "id",
            "created_at",
            "title",
            "configuration",
            "assigned_customers",
            "mobile_hide",
            "mobile_order",
            "image",
            "external_id",
            "tenant",
        )
        read_only_fields = fields


class DashboardUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email")


class DashboardRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "name")


class DashboardSerializer(serializers.ModelSerializer):
    """
    A dashboard of the caller's hotel, optionally handed out to users and/or roles.

    Assignment lives on the user/role side (`User.dashboards`, `Role.dashboards`). `user_ids` and
    `role_ids` replace the full set of holders of that kind; leaving a field out keeps it as is.
    """

    user_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.filter(is_active=True), write_only=True, required=False
    )
    role_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Role.objects.all(), write_only=True, required=False
    )
    users = serializers.SerializerMethodField()
    roles = DashboardRoleSerializer(many=True, read_only=True)

    def get_users(self, instance):
        # Filtered in Python so a prefetched `users` is reused.
        active = [user for user in instance.users.all() if user.is_active]
        return DashboardUserSerializer(active, many=True).data

    def validate_user_ids(self, value):
        tenant_id = self.context.get("tenant_id")
        outsiders = [user.email for user in value if str(user.tenant_id) != str(tenant_id)]
        if outsiders:
            raise serializers.ValidationError(f"User out of scope: {', '.join(outsiders)}.")
        return value

    def validate_role_ids(self, value):
        tenant_id = self.context.get("tenant_id")
        outsiders = [role.name for role in value if str(role.tenant_id) != str(tenant_id)]
        if outsiders:
            raise serializers.ValidationError(f"Role out of scope: {', '.join(outsiders)}.")
        return value

    def create(self, validated_data):
        users = validated_data.pop("user_ids", None)
        roles = validated_data.pop("role_ids", None)
        instance = super().create(validated_data)
        self._assign(instance, users, roles)
        return instance

    def update(self, instance, validated_data):
        users = validated_data.pop("user_ids", None)
        roles = validated_data.pop("role_ids", None)
        instance = super().update(instance, validated_data)
        self._assign(instance, users, roles)
        return instance

    @staticmethod
    def _assign(instance, users, roles):
        if users is not None:
            # Deactivated holders are hidden from the API, so a PUT cannot mention them; keep them
            # rather than silently dropping their assignment.
            instance.users.set([*users, *instance.users.filter(is_active=False)])
        if roles is not None:
            instance.roles.set(roles)

    def validate_title(self, value):
        tenant_id = self.context.get("tenant_id")
        if not self.instance:
            original_title = re.sub(r"\sCopy\s\d+$", "", value)
            new_title = original_title
            counter = 1
            while Dashboard.objects.filter(tenant_id=tenant_id, title__iexact=new_title).exists():
                new_title = f"{original_title} Copy {counter}"
                counter += 1
            value = new_title
        return value

    class Meta:
        model = Dashboard
        fields = (
            "id",
            "created_at",
            "title",
            "configuration",
            "assigned_customers",
            "mobile_hide",
            "mobile_order",
            "image",
            "external_id",
            "tenant",
            "user_ids",
            "role_ids",
            "users",
            "roles",
        )
        extra_kwargs = {
            "tenant": {"read_only": True},
        }


class DashboardFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("title", "-title", "created_at", "-created_at")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("title",), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)


class DashboardTypeSerializer(ValidatorSerializer):
    type = serializers.ChoiceField(choices=[Dashboard.MAIN_DASHBOARD, Dashboard.PUBLIC_SPACE_DASHBOARD])


class DashboardQuickFilterParams(DashboardFilterParams):
    page = None
    size = None
    sort_by = None
    search_field = None
