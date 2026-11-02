from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.serializers.dashboard import DashboardSerializer
from users.models import Role, User
from users.serializers.user import SimpleUserSerializer


class SimpleRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "name")


class UserDashboardSerializer(DashboardSerializer):
    """
    A dashboard handed out to users and/or roles.

    Assignment lives on the user/role side (`User.dashboards`, `Role.dashboards`), so the
    ids passed here replace the full set of holders: anyone left out is unassigned.
    """

    user_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.filter(is_active=True), write_only=True, required=False
    )
    role_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Role.objects.all(), write_only=True, required=False
    )
    users = serializers.SerializerMethodField()
    roles = SimpleRoleSerializer(many=True, read_only=True)

    def get_users(self, instance):
        # Filtered in Python so a prefetched `users` is reused.
        active = [user for user in instance.users.all() if user.is_active]
        return SimpleUserSerializer(active, many=True).data

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

    def validate(self, attrs):
        attrs = super().validate(attrs)
        users = attrs.get("user_ids", self.instance.users.filter(is_active=True) if self.instance else [])
        roles = attrs.get("role_ids", self.instance.roles.all() if self.instance else [])
        # Without holders the dashboard would silently drop out of this endpoint.
        if not users and not roles:
            raise serializers.ValidationError({"non_field_errors": "Assign the dashboard to a user or a role."})
        return attrs

    def create(self, validated_data):
        users = validated_data.pop("user_ids", [])
        roles = validated_data.pop("role_ids", [])
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

    class Meta(DashboardSerializer.Meta):
        fields = (*DashboardSerializer.Meta.fields, "user_ids", "role_ids", "users", "roles")


class DashboardOrderSerializer(ValidatorSerializer):
    """The caller's dashboards in the order they want them; the list is taken as a whole."""

    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=True)

    def validate_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Dashboard ids must be unique.")
        available = set(self.context["available"].order_by().values_list("pk", flat=True))
        unknown = [str(pk) for pk in value if pk not in available]
        if unknown:
            raise serializers.ValidationError(f"Dashboard not available: {', '.join(unknown)}.")
        return value
