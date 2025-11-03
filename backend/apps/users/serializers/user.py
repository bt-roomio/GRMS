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
        swagger_schema_fields = {
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
    roles = serializers.PrimaryKeyRelatedField(many=True, queryset=Role.objects.all(), required=False)
    additional_info = serializers.JSONField(required=False, help_text="{excluded_fields: ['phone', 'email']}")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_at"] = instance.date_joined
        return data

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
            "roles",
            "is_active",
        )
        extra_kwargs = {
            "is_superuser": {"read_only": True},
        }


class UserDetailSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["roles"] = RoleSimpleSerializer(instance.roles, many=True).data
        data["tenant_name"] = instance.tenant.title
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
            "roles",
            "is_active",
        )
        extra_kwargs = {
            "is_superuser": {"read_only": True},
        }


class UserParams(ValidatorSerializer):
    SORT_FIELDS = ("first_name", "-first_name", "email", "-email")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    send_activation_mail = serializers.BooleanField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
    search_field = serializers.ChoiceField(choices=("first_name", "email", "phone"), required=False)
    search_value = serializers.CharField(required=False)
