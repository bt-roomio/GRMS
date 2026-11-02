from django.contrib.auth.models import Permission

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Dashboard
from main.serializers.dashboard import SimpleDashboardSerializer
from users.models import Role


class PermissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "name", "codename", "content_type")


class PermissionRelatedField(serializers.PrimaryKeyRelatedField):
    """Accepts a bare permission id or the object shape returned by ``PermissionsSerializer``."""

    default_error_messages = {
        "missing_id": 'Expected a permission id or an object with an "id" key.',
    }

    def to_internal_value(self, data):
        if isinstance(data, dict):
            if "id" not in data:
                self.fail("missing_id")
            data = data["id"]
        return super().to_internal_value(data)


class RoleSimpleSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        perms = instance.permissions
        data["permissions"] = PermissionsSerializer(perms, many=True).data if perms else []
        data["dashboards"] = SimpleDashboardSerializer(instance.dashboards.all(), many=True).data
        return data

    class Meta:
        model = Role
        fields = ("id", "name", "permissions", "additional_info", "tenant", "dashboards")
        extra_kwargs = {"tenant": {"read_only": True}}


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionRelatedField(queryset=Permission.objects.all(), many=True, required=True)
    dashboards = serializers.PrimaryKeyRelatedField(queryset=Dashboard.objects.all(), many=True, required=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["permissions"] = (
            PermissionsSerializer(instance.permissions, many=True).data if instance.permissions else []
        )
        data["dashboards"] = SimpleDashboardSerializer(instance.dashboards.all(), many=True).data
        return data

    def validate_dashboards(self, value):
        """Dashboards must live in the same hotel as the role; a global role has no hotel to take them from."""
        tenant_id = self.instance.tenant_id if self.instance else self.context.get("tenant_id")
        if value and not tenant_id:
            raise serializers.ValidationError("A role without a tenant cannot hold dashboards.")
        outsiders = [d.title for d in value if str(d.tenant_id) != str(tenant_id)]
        if outsiders:
            raise serializers.ValidationError(f"Dashboard out of scope: {', '.join(outsiders)}.")
        return value

    def update(self, instance, validated_data):
        name = validated_data.get("name", instance.name)

        if instance.name != name:
            clash = Role.objects.filter(name=name, tenant=instance.tenant).exclude(pk=instance.pk)
            if clash.exists():
                raise serializers.ValidationError({"name": "A role with this name already exists for this tenant."})

        return super().update(instance, validated_data)

    class Meta:
        model = Role
        fields = ("id", "name", "permissions", "additional_info", "tenant", "dashboards")
        extra_kwargs = {"tenant": {"read_only": True}}


class RoleQuickFilterParams(ValidatorSerializer):
    search_value = serializers.CharField(required=False)
