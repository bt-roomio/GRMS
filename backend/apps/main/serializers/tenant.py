from datetime import datetime

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Tenant


class TenantFilterParams(ValidatorSerializer):
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[
                "-created_at",
                "created_at",
                "title",
                "-title",
            ],
            default="-created_at",
        ),
        required=False,
    )
    search_field = serializers.ChoiceField(choices=("title",), required=False)
    search_value = serializers.CharField(required=False)


class TenantSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        instance.created_at = (
            datetime.fromtimestamp(instance.created_at / 1000)
            if isinstance(instance.created_at, int)
            else instance.created_at
        )
        data = super().to_representation(instance)

        data["online_rooms"] = instance.online_rooms
        data["offline_rooms"] = instance.offline_rooms
        data["total_rooms"] = instance.total_rooms
        return data

    class Meta:
        model = Tenant
        fields = (
            "id",
            "created_at",
            "tenant_profile",
            "additional_info",
            "address",
            "address2",
            "city",
            "country",
            "email",
            "phone",
            "region",
            "state",
            "title",
            "zip",
        )
