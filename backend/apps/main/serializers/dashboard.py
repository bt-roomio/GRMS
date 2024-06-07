from core.utils.serializers import ValidatorSerializer
from main.models import Dashboard
from rest_framework import serializers


class DashboardSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["tenant"] = instance.tenant_id
        return data

    class Meta:
        model = Dashboard
        fields = (
            "id",
            "title",
            "configuration",
            "assigned_customers",
            "mobile_hide",
            "mobile_order",
            "image",
            "external_id",
        )


class DashboardFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
