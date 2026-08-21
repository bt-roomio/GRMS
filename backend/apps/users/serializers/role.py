from django.contrib.auth.models import Permission

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from users.models import Role


class PermissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "name", "codename", "content_type")


class RoleSimpleSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        perms = instance.permissions
        data["permissions"] = PermissionsSerializer(perms, many=True).data if perms else []
        return data

    class Meta:
        model = Role
        fields = ("id", "name", "permissions", "additional_info", "tenant")
        extra_kwargs = {"tenant": {"read_only": True}}


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(queryset=Permission.objects.all(), many=True, required=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["permissions"] = (
            PermissionsSerializer(instance.permissions, many=True).data if instance.permissions else []
        )
        return data

    def update(self, instance, validated_data):
        name = validated_data.get("name", instance.name)

        if instance.name != name:
            clash = Role.objects.filter(name=name, tenant=instance.tenant).exclude(pk=instance.pk)
            if clash.exists():
                raise serializers.ValidationError({"name": "A role with this name already exists for this tenant."})

        return super().update(instance, validated_data)

    class Meta:
        model = Role
        fields = ("id", "name", "permissions", "additional_info", "tenant")
        extra_kwargs = {"tenant": {"read_only": True}}


class RoleQuickFilterParams(ValidatorSerializer):
    search_value = serializers.CharField(required=False)
