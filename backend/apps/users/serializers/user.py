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
    SORT_FIELDS = ("first_name", "-first_name", "email", "-email")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    send_activation_mail = serializers.BooleanField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
    search_field = serializers.ChoiceField(choices=("first_name", "email", "phone"), required=False)
    search_value = serializers.CharField(required=False)
