from core.utils.serializers import ValidatorSerializer
from rest_framework import serializers
from users.models import User


class UserSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["authority"] = [group.name for group in instance.groups.all()]
        return data

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email", "additional_info", "phone", "created_at", "tenant_id")


class UserParams(ValidatorSerializer):
    sendActivationMail = serializers.BooleanField(required=False)
