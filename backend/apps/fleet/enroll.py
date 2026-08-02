import logging
import secrets

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from core.utils.get_time import get_mil_sec
from fleet.models import FleetAuditLog, FleetNode
from fleet.netbird.client import NetBirdClient
from fleet.netbird.exceptions import NetBirdAPIError, NetBirdError
from fleet.utils.audit import log_action

logger = logging.getLogger(__name__)

TOKEN_BYTES = 32

# Wiped whenever the peer is torn down, so the next `netbird up` pins a fresh one.
PEER_STATE_FIELDS = (
    "netbird_peer_id",
    "mesh_ip",
    "is_online",
    "last_seen",
    "enrolled_at",
    "os",
    "netbird_version",
    "ssh_host_key",
)


class EnrollmentError(Exception):
    """The install request is not valid — expired, already used, or unknown."""


# -- peer lifecycle --------------------------------------------------------


def release_peer(node: FleetNode, client=None, user=None) -> None:
    """
    Delete this node's NetBird peer and its setup key, then forget both.

    A 404 counts as released. Anything else propagates: silently leaving a live
    peer behind would break the one-active-peer-per-gateway rule.
    """
    client = client or NetBirdClient()

    if node.netbird_peer_id:
        try:
            client.delete_peer(node.netbird_peer_id)
        except NetBirdAPIError as exc:
            if exc.status_code != 404:
                raise
        log_action(
            FleetAuditLog.ACTION.PEER_DELETED,
            node=node,
            user=user,
            detail={"peer_id": node.netbird_peer_id, "mesh_ip": node.mesh_ip},
        )

    if node.netbird_setup_key_id:
        try:
            client.delete_setup_key(node.netbird_setup_key_id)
        except NetBirdAPIError as exc:
            if exc.status_code != 404:
                raise
        log_action(
            FleetAuditLog.ACTION.SETUP_KEY_DELETED,
            node=node,
            user=user,
            detail={"setup_key_id": node.netbird_setup_key_id},
        )

    for field in PEER_STATE_FIELDS:
        setattr(node, field, FleetNode._meta.get_field(field).get_default())

    node.netbird_setup_key_id = None
    node.netbird_setup_key = None
    node.save(update_fields=[*PEER_STATE_FIELDS, "netbird_setup_key_id", "netbird_setup_key", "updated_at"])


def mint_setup_key(node: FleetNode, client=None, user=None) -> str:
    """
    Create a single-use NetBird setup key for exactly one machine.

    Auto-grouped into the hotel group, so a node can never land in the
    privileged `backend` group by accident, and short-lived — there is no
    shared master key to leak.
    """
    client = client or NetBirdClient()
    key = client.create_setup_key(
        name=f"node-{node.code}",
        auto_groups=([settings.NETBIRD_HOTEL_GROUP_ID] if settings.NETBIRD_HOTEL_GROUP_ID else []),
        usage_limit=1,
        expires_in=settings.NETBIRD_SETUP_KEY_TTL,
    )
    plaintext = key.get("key")
    if not plaintext:
        raise EnrollmentError("NetBird did not return a setup key")

    node.netbird_setup_key_id = key.get("id")
    node.netbird_setup_key = plaintext
    node.save(update_fields=["netbird_setup_key_id", "netbird_setup_key", "updated_at"])

    log_action(
        FleetAuditLog.ACTION.SETUP_KEY_CREATED,
        node=node,
        user=user,
        detail={"setup_key_id": node.netbird_setup_key_id, "expires_in": settings.NETBIRD_SETUP_KEY_TTL},
    )
    return plaintext


def prepare_enrollment(node: FleetNode, user=None) -> str:
    """
    Bring the node to "ready to enrol" and hand back the fresh setup key.

    Whatever it had before — nothing, a live peer, a spent key — it ends up
    with exactly one unused single-use key and no peer, which is what keeps one
    active peer per gateway true. The peer itself is created on the VM by
    `netbird up`; NetBird has no API to create one server-side.
    """
    client = NetBirdClient()

    if node.netbird_peer_id or node.netbird_setup_key_id:
        release_peer(node, client=client, user=user)

    setup_key = mint_setup_key(node, client=client, user=user)
    issue_install_token(node, user=user)
    return setup_key


# -- install token ---------------------------------------------------------


def issue_install_token(node: FleetNode, user=None) -> FleetNode:
    """
    Mint a fresh one-time install token, invalidating any previous link.

    The link must not outlive the key it hands out, so the shorter TTL wins.
    """
    ttl_ms = min(
        settings.FLEET_INSTALL_TOKEN_TTL_HOURS * 3600 * 1000,
        settings.NETBIRD_SETUP_KEY_TTL * 1000,
    )

    node.install_token = secrets.token_urlsafe(TOKEN_BYTES)
    node.token_expires_at = get_mil_sec() + ttl_ms
    node.token_used_at = None
    node.save(update_fields=["install_token", "token_expires_at", "token_used_at", "updated_at"])

    log_action(
        FleetAuditLog.ACTION.TOKEN_ISSUED,
        node=node,
        user=user,
        detail={"expires_at": node.token_expires_at},
    )
    return node


def install_url(node: FleetNode, request=None) -> str:
    base = settings.FLEET_INSTALL_BASE_URL
    if not base and request is not None:
        base = request.build_absolute_uri("/").rstrip("/")
    return f"{base}/install/{node.code}?t={node.install_token}"


def install_command(node: FleetNode, request=None) -> str:
    return f"curl -fsSL '{install_url(node, request)}' | sudo bash"


def verify_install_token(node: FleetNode, token: str) -> None:
    """Raise EnrollmentError unless the token matches, is unused and unexpired."""
    if not node.install_token or not token:
        raise EnrollmentError("no install token issued")

    if not secrets.compare_digest(node.install_token, token):
        raise EnrollmentError("token mismatch")

    if node.token_used_at:
        raise EnrollmentError("token already used")

    if not node.token_expires_at or node.token_expires_at < get_mil_sec():
        raise EnrollmentError("token expired")

    if not node.netbird_setup_key:
        raise EnrollmentError("setup key already consumed")


# -- script ----------------------------------------------------------------


def render_bootstrap(node: FleetNode, setup_key: str) -> str:
    """
    Render the per-node bootstrap script.

    Every value is baked in as a literal: shell variables live only inside one
    shell process, so a paste interrupted halfway silently loses them.
    """
    return render_to_string(
        "fleet/bootstrap.sh",
        {
            "code": node.code,
            "setup_key": setup_key,
            "management_url": settings.NETBIRD_MANAGEMENT_URL,
            "public_key": settings.FLEET_SSH_PUBLIC_KEY.strip(),
            "ssh_user": node.ssh_user or settings.FLEET_SSH_USER,
            "ssh_home": f"/home/{node.ssh_user or settings.FLEET_SSH_USER}",
            "generated_at": timezone.now().isoformat(timespec="seconds"),
        },
    )


def consume_token(node: FleetNode) -> None:
    """Burn the token and drop the plaintext key — it is single-use anyway."""
    node.token_used_at = get_mil_sec()
    node.netbird_setup_key = None
    node.save(update_fields=["token_used_at", "netbird_setup_key", "updated_at"])


__all__ = [
    "EnrollmentError",
    "NetBirdError",
    "consume_token",
    "install_command",
    "install_url",
    "issue_install_token",
    "mint_setup_key",
    "prepare_enrollment",
    "release_peer",
    "render_bootstrap",
    "verify_install_token",
]
