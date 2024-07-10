from core.utils.serializers import ValidatorSerializer
from django.contrib.auth.models import Group
from rest_framework import serializers
from users.models import User


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=Group.objects.all())

    def create(self, validated_data):
        groups_data = validated_data.pop("groups")
        user = User.objects.create(**validated_data)
        user.groups.set(groups_data)
        return user

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "additional_info",
            "phone",
            "created_at",
            "tenant_id",
            "groups",
        )


class UserParams(ValidatorSerializer):
    sendActivationMail = serializers.BooleanField(required=False)
