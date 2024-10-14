from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Dashboard


class SimpleDashboardSerializer(serializers.ModelSerializer):
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


class DashboardSerializer(serializers.ModelSerializer):
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
            "tenant",
        )


class DashboardFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)


class DashboardTypeSerializer(ValidatorSerializer):
    type = serializers.ChoiceField(choices=[Dashboard.MAIN_DASHBOARD, Dashboard.PUBLIC_SPACE_DASHBOARD])
