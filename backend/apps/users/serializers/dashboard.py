from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer


class DashboardOrderSerializer(ValidatorSerializer):
    """The caller's dashboards in the order they want them; the list is taken as a whole."""

    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=True)

    def validate_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Dashboard ids must be unique.")
        available = set(self.context["available"].order_by().values_list("pk", flat=True))
        unknown = [str(pk) for pk in value if pk not in available]
        if unknown:
            raise serializers.ValidationError(f"Dashboard not available: {', '.join(unknown)}.")
        return value
