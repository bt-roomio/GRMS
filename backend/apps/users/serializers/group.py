from django.contrib.auth.models import Group, Permission
from rest_framework import serializers


class PermissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "name", "codename", "content_type")


class GroupSimpleSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["permissions"] = (
            PermissionsSerializer(instance.permissions, many=True).data if instance.permissions else []
        )
        return data

    class Meta:
        model = Group
        fields = ("id", "name", "permissions")


class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(queryset=Permission.objects.all(), many=True)

    def validate(self, attrs):
        if self.instance:
            if "name" not in attrs:
                attrs["name"] = self.instance.name
            if "permissions" not in attrs:
                attrs["permissions"] = list()
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["permissions"] = PermissionsSerializer(instance.permissions, many=True).data
        return data

    def create(self, validated_data):
        user = self.context.get("request").user
        permissions = validated_data.pop("permissions")
        group = Group.objects.create(**validated_data)
        user.groups.add(group)
        for permission in permissions:
            permission = Permission.objects.get(id=permission.id)
            group.permissions.add(permission.id)
        return group

    def update(self, instance, validated_data):
        user = self.context.get("request").user
        user.groups.add(instance)
        return super().update(instance, validated_data)

    class Meta:
        model = Group
        fields = ("id", "name", "permissions")
