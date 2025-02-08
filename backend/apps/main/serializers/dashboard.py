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
            "tenant",
        )


class DashboardFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("title", "-title")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)


class DashboardTypeSerializer(ValidatorSerializer):
    type = serializers.ChoiceField(choices=[Dashboard.MAIN_DASHBOARD, Dashboard.PUBLIC_SPACE_DASHBOARD])
