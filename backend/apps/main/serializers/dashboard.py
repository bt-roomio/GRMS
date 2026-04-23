import re

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Dashboard


class SimpleDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = (
            "id",
            "title",
            "assigned_customers",
            "mobile_hide",
            "mobile_order",
            "image",
            "external_id",
        )


class DashboardSerializer(serializers.ModelSerializer):
    def validate_title(self, value):
        tenant_id = self.context.get("tenant_id")
        if not self.instance:
            original_title = re.sub(r"\sCopy\s\d+$", "", value)
            new_title = original_title
            counter = 1
            while Dashboard.objects.filter(tenant_id=tenant_id, title__iexact=new_title).exists():
                new_title = f"{original_title} Copy {counter}"
                counter += 1
            value = new_title
        return value

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
        extra_kwargs = {
            "tenant": {"read_only": True},
        }


class DashboardFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("title", "-title", "created_at", "-created_at")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("title",), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)


class DashboardTypeSerializer(ValidatorSerializer):
    type = serializers.ChoiceField(choices=[Dashboard.MAIN_DASHBOARD, Dashboard.PUBLIC_SPACE_DASHBOARD])


class DashboardQuickFilterParams(DashboardFilterParams):
    page = None
    size = None
    sort_by = None
    search_field = None
