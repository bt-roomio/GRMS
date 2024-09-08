from rest_framework import serializers

from main.models import Tenant


class TenantSerializer(serializers.ModelSerializer):
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
