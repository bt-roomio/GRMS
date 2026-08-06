from django.db import models
from django.db.models import CASCADE, SET_NULL, Q, UniqueConstraint

from core.models import BaseModel, UpdateByModel
from core.utils.unix_timestamp import UnixTimeStampField
from fleet.querysets.audit_log import FleetAuditLogQuerySet
from fleet.querysets.fleet_node import FleetNodeQuerySet


class FleetNode(BaseModel, UpdateByModel):
    """
    The VM that hosts one gateway, reachable over the NetBird mesh.

    The gateway is an IoT gateway *device* (``Device.additional_info["gateway"]``);
    the node is the machine running it.
    """

    # One active node per gateway. The gateway also decides the tenant.
    gateway = models.ForeignKey("main.Device", CASCADE, related_name="fleet_nodes")
    # Denormalised from ``gateway.tenant`` so scoping and the poller stay single-table.
    tenant = models.ForeignKey("main.Tenant", CASCADE, related_name="fleet_nodes")

    # ``{tenant_slug}_{gateway_slug}`` — also used verbatim as the NetBird
    # hostname, which is how the poller matches a peer back to this row.
    code = models.CharField(max_length=128, editable=False)

    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    # Filled in by the poller once the node joins the mesh.
    netbird_peer_id = models.CharField(max_length=64, null=True, blank=True, unique=True)
    mesh_ip = models.GenericIPAddressField(null=True, blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = UnixTimeStampField(null=True, blank=True)
    enrolled_at = UnixTimeStampField(null=True, blank=True)
    os = models.CharField(max_length=255, null=True, blank=True)
    netbird_version = models.CharField(max_length=64, null=True, blank=True)

    ssh_user = models.CharField(max_length=64, default="roomio-agent")
    # Trust-on-first-use pin, OpenSSH format. Recorded on the first successful
    # connection and enforced on every one after it.
    ssh_host_key = models.TextField(null=True, blank=True)

    # One-time install token handed out with the "Install agent" one-liner.
    install_token = models.CharField(max_length=128, null=True, blank=True)
    token_expires_at = UnixTimeStampField(null=True, blank=True)
    token_used_at = UnixTimeStampField(null=True, blank=True)

    # The id lets us delete the key on re-enrollment. The plaintext is held only
    # until ``/install/<code>`` renders it, then wiped with the token.
    netbird_setup_key_id = models.CharField(max_length=64, null=True, blank=True)
    netbird_setup_key = models.CharField(max_length=128, null=True, blank=True)

    is_active = models.BooleanField(default=True)

    objects = FleetNodeQuerySet.as_manager()

    def __str__(self) -> str:
        return self.code

    @property
    def is_enrolled(self) -> bool:
        return bool(self.netbird_peer_id and self.mesh_ip)

    class Meta(BaseModel.Meta):
        db_table = "fleet_node"
        constraints = [
            # Partial rather than OneToOneField: nodes are soft-deleted, and a
            # plain unique would permanently block re-enrolling a gateway.
            UniqueConstraint("gateway", condition=Q(is_active=True), name="unique_active_fleet_node_gateway"),
            UniqueConstraint("code", condition=Q(is_active=True), name="unique_active_fleet_node_code"),
        ]
        indexes = [
            models.Index(fields=["code"], name="fleet_node_code_idx"),
        ]
        permissions = [
            ("enroll_fleetnode", "Can issue install tokens for fleet nodes"),
            ("terminal_fleetnode", "Can open a terminal on a fleet node"),
            ("exec_fleetnode", "Can run commands on a fleet node"),
            ("upload_fleetnode", "Can upload files to a fleet node"),
        ]


class FleetAuditLog(BaseModel):
    """Append-only record of every privileged action taken against a node."""

    class ACTION(models.TextChoices):
        TOKEN_ISSUED = "token_issued", "Install token issued"
        BOOTSTRAP_SERVED = "bootstrap_served", "Bootstrap script served"
        BOOTSTRAP_REJECTED = "bootstrap_rejected", "Bootstrap request rejected"
        PEER_PINNED = "peer_pinned", "NetBird peer pinned"
        PEER_MISMATCH = "peer_mismatch", "NetBird peer id mismatch"
        PEER_DELETED = "peer_deleted", "NetBird peer deleted"
        SETUP_KEY_CREATED = "setup_key_created", "NetBird setup key created"
        SETUP_KEY_DELETED = "setup_key_deleted", "NetBird setup key deleted"
        HOST_KEY_PINNED = "host_key_pinned", "SSH host key pinned"
        HOST_KEY_MISMATCH = "host_key_mismatch", "SSH host key mismatch"
        COMMAND_RUN = "command_run", "Command executed"
        TERMINAL_OPEN = "terminal_open", "Terminal session opened"
        TERMINAL_CLOSE = "terminal_close", "Terminal session closed"
        TERMINAL_DENIED = "terminal_denied", "Terminal session denied"
        FILE_UPLOADED = "file_uploaded", "File uploaded"
        FILE_UPLOAD_FAILED = "file_upload_failed", "File upload failed"

    user = models.ForeignKey("users.User", SET_NULL, null=True, blank=True, related_name="fleet_audit_logs")
    node = models.ForeignKey("fleet.FleetNode", SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=32, choices=ACTION.choices)
    detail = models.JSONField(null=True, blank=True)
    remote_addr = models.GenericIPAddressField(null=True, blank=True)

    objects = FleetAuditLogQuerySet.as_manager()

    def __str__(self) -> str:
        return f"{self.action} ({self.node_id})"

    class Meta(BaseModel.Meta):
        db_table = "fleet_audit_log"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["node", "-created_at"], name="fleet_audit_node_ts_idx"),
        ]
