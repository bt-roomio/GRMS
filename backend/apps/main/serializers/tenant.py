from datetime import datetime

from rest_framework import serializers

from main.models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        instance.created_at = (
            datetime.fromtimestamp(instance.created_at / 1000)
            if isinstance(instance.created_at, int)
            else instance.created_at
        )
        data = super().to_representation(instance)
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
