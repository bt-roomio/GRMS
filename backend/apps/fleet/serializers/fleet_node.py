from django.conf import settings

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from fleet.models import FleetAuditLog, FleetNode
from fleet.utils.code import build_code
from main.models import Device
from users.serializers.user import SimpleUserSerializer


class FleetNodeSerializer(serializers.ModelSerializer):
    created_by = SimpleUserSerializer(read_only=True)
    is_enrolled = serializers.BooleanField(read_only=True)
    tenant_title = serializers.CharField(source="tenant.title", read_only=True)
    gateway_name = serializers.CharField(source="gateway.name", read_only=True)

    class Meta:
        model = FleetNode
        fields = (
            "id",
            "code",
            "title",
            "description",
            "gateway",
            "gateway_name",
            "tenant",
            "tenant_title",
            "mesh_ip",
            "is_online",
            "is_enrolled",
            "last_seen",
            "enrolled_at",
            "os",
            "netbird_version",
            "ssh_user",
            "created_at",
            "created_by",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "code",
            "gateway",
            "tenant",
            "mesh_ip",
            "is_online",
            "last_seen",
            "enrolled_at",
            "os",
            "netbird_version",
            "ssh_user",
            "created_at",
            "updated_at",
        )


class SimpleFleetNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FleetNode
        fields = ("id", "code", "title", "mesh_ip", "is_online")


class FleetNodeCreateSerializer(serializers.ModelSerializer):
    """
    Creation only assigns identity; peer id, mesh ip and host key are filled in
    later by the poller and the first SSH connection.

    The gateway is the whole payload — it decides the tenant and the code.
    """

    gateway = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())

    class Meta:
        model = FleetNode
        fields = ("gateway", "title", "description")

    def validate_gateway(self, gateway):
        if not (gateway.additional_info or {}).get("gateway"):
            raise serializers.ValidationError(f"'{gateway.name}' is a device, not a gateway.")

        if not gateway.is_active:
            raise serializers.ValidationError(f"'{gateway.name}' is deactivated.")

        scope = self.context.get("tenant_scope")
        if scope is not None and str(gateway.tenant_id) != str(scope):
            # Same answer as an unknown id — never confirm a foreign gateway exists.
            raise serializers.ValidationError("Unknown gateway.")

        if FleetNode.objects.for_gateway(gateway.id) is not None:
            raise serializers.ValidationError(f"'{gateway.name}' already has an active fleet node.")

        return gateway

    def create(self, validated_data):
        gateway = validated_data["gateway"]
        validated_data["tenant"] = gateway.tenant
        validated_data["code"] = build_code(gateway.tenant, gateway)
        validated_data.setdefault("ssh_user", settings.FLEET_SSH_USER)
        return super().create(validated_data)


class FleetNodeUpdateSerializer(serializers.ModelSerializer):
    """
    Identity is fixed at creation and mesh state belongs to the poller, so
    neither is accepted here.
    """

    class Meta:
        model = FleetNode
        fields = ("title", "description")


class FleetNodeFilterParams(ValidatorSerializer):
    SORT_FIELDS = (
        "code",
        "-code",
        "title",
        "-title",
        "is_online",
        "-is_online",
        "last_seen",
        "-last_seen",
        "created_at",
        "-created_at",
    )

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=15)
    search_value = serializers.CharField(required=False)
    is_online = serializers.BooleanField(required=False, allow_null=True, default=None)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)


class InstallCommandSerializer(serializers.Serializer):
    """Everything the UI needs to render the install instructions."""

    install_url = serializers.CharField(read_only=True, help_text="One-time link that serves the bootstrap script.")
    command = serializers.CharField(read_only=True, help_text="curl … | sudo bash — needs the VM to reach this server.")
    hostname = serializers.CharField(read_only=True, help_text="The NetBird peer name this node will register as.")
    peer_replaced = serializers.BooleanField(
        read_only=True,
        help_text="True when an existing peer and its setup key were deleted to make room for this one.",
    )
    expires_at = serializers.IntegerField(read_only=True)


class RunCommandSerializer(ValidatorSerializer):
    command = serializers.CharField(max_length=4096)
    timeout = serializers.FloatField(required=False, min_value=1, max_value=600)


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
