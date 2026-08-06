from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from fleet.models import FleetAuditLog
from users.serializers.user import SimpleUserSerializer


class FleetAuditLogSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    node_code = serializers.CharField(source="node.code", read_only=True)

    class Meta:
        model = FleetAuditLog
        fields = (
            "id",
            "action",
            "user",
            "node",
            "node_code",
            "detail",
            "remote_addr",
            "created_at",
        )


class FleetAuditLogFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=15)
    action = serializers.ChoiceField(choices=FleetAuditLog.ACTION.choices, required=False)
