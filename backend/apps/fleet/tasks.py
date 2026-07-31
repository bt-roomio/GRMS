import logging

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings

from core.utils.get_time import get_mil_sec
from fleet.models import FleetAuditLog, FleetNode
from fleet.netbird.client import NetBirdClient
from fleet.netbird.exceptions import NetBirdError, NetBirdNotConfigured
from fleet.utils.audit import log_action
from fleet.utils.time import to_mil_sec

logger = logging.getLogger(__name__)

# Fields the poller owns. Anything not listed here is never touched by polling.
PEER_FIELDS = (
    "netbird_peer_id",
    "mesh_ip",
    "is_online",
    "last_seen",
    "os",
    "netbird_version",
    "enrolled_at",
)


def peer_name(peer) -> str:
    """
    The identifier the node joined with (`netbird up --hostname <code>`).

    Only `name` carries it. `hostname` is the VM's own OS hostname and
    `dns_label` is the DNS-safe form (`noe_hotel` -> `noe-hotel.…`), so both
    silently match nothing. No fallback: this decides where we open a root
    shell, so it is exact or it does not happen.
    """
    return peer.get("name") or ""


def apply_peer(node: FleetNode, peer: dict) -> bool:
    """
    Copy peer state onto the node. Returns True if anything changed.

    The peer id is pinned on first sight: a second machine claiming the same
    name gets a different id and is refused, or it would repoint `mesh_ip` and
    we would run commands on the attacker's box.
    """
    peer_id = peer.get("id")

    if node.netbird_peer_id and peer_id and node.netbird_peer_id != peer_id:
        logger.warning(
            "Peer id mismatch for %s: pinned=%s incoming=%s — ignoring",
            node.code,
            node.netbird_peer_id,
            peer_id,
        )
        log_action(
            FleetAuditLog.ACTION.PEER_MISMATCH,
            node=node,
            detail={
                "pinned": node.netbird_peer_id,
                "incoming": peer_id,
                "incoming_ip": peer.get("ip"),
            },
        )
        return False

    first_pin = not node.netbird_peer_id

    updates = {
        "netbird_peer_id": peer_id,
        "mesh_ip": peer.get("ip") or node.mesh_ip,
        "is_online": bool(peer.get("connected")),
        "last_seen": to_mil_sec(peer.get("last_seen")) or node.last_seen,
        "os": peer.get("os") or node.os,
        "netbird_version": peer.get("version") or node.netbird_version,
    }
    if first_pin:
        updates["enrolled_at"] = node.enrolled_at or get_mil_sec()

    changed = [field for field, value in updates.items() if getattr(node, field) != value]
    if not changed:
        return False

    for field, value in updates.items():
        setattr(node, field, value)
    node.save(update_fields=[*changed, "updated_at"])

    if first_pin:
        log_action(
            FleetAuditLog.ACTION.PEER_PINNED,
            node=node,
            detail={"peer_id": peer_id, "mesh_ip": node.mesh_ip},
        )

    return True


def sweep_unconfirmed(confirmed_ids) -> list:
    """
    Force offline every node this poll did not confirm as connected.

    Never second-guesses a fresh `connected: true` against `last_seen`: NetBird
    does not always refresh that field, so doing so flaps nodes every cycle.
    """
    stale = FleetNode.objects.is_active().filter(is_online=True).exclude(id__in=confirmed_ids)
    stale_ids = list(stale.values_list("id", flat=True))
    stale.update(is_online=False, updated_at=get_mil_sec())
    return stale_ids


def sweep_lagging() -> list:
    """
    Fallback for when NetBird itself is unreachable.

    Nothing can be confirmed, so anything unsighted for
    FLEET_OFFLINE_AFTER_SECONDS drops offline rather than sitting green on
    stale information.
    """
    cutoff = get_mil_sec() - settings.FLEET_OFFLINE_AFTER_SECONDS * 1000

    lagging = FleetNode.objects.is_active().filter(is_online=True, last_seen__isnull=False, last_seen__lt=cutoff)
    lagging_ids = list(lagging.values_list("id", flat=True))
    lagging.update(is_online=False, updated_at=get_mil_sec())
    return lagging_ids


def notify(node_ids) -> None:
    """Nudge subscribed WebSocket clients so the status dot repaints."""
    if not node_ids:
        return

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    tenant_ids = set(FleetNode.objects.filter(id__in=node_ids).values_list("tenant_id", flat=True).distinct())
    for tenant_id in tenant_ids:
        try:
            async_to_sync(channel_layer.group_send)(
                f"fleet_nodes_{tenant_id}",
                {"type": "fleet.node.update"},
            )
        except Exception:
            logger.exception("Failed to push fleet update for tenant %s", tenant_id)


@shared_task(name="fleet.tasks.poll_fleet_peers", ignore_result=True)
def poll_fleet_peers():
    """
    Reconcile FleetNode rows against NetBird's peer list.

    "Online" means connected to the mesh, not that the stack inside the VM is
    healthy.
    """
    try:
        client = NetBirdClient()
    except NetBirdNotConfigured:
        logger.debug("Fleet poller skipped: NetBird is not configured")
        return

    try:
        peers = client.list_peers(group_id=settings.NETBIRD_HOTEL_GROUP_ID or None)
    except NetBirdError:
        logger.exception("Fleet poller could not reach the NetBird API")
        notify(sweep_lagging())
        return

    by_code = {peer_name(peer): peer for peer in peers if peer_name(peer)}
    nodes = FleetNode.objects.is_active().filter(code__in=by_code.keys()) if by_code else []

    unmatched = set(by_code) - {node.code for node in nodes}
    if unmatched:
        # Almost always a wrong --hostname, which is otherwise invisible: the
        # node just sits offline with no error anywhere.
        logger.warning("Fleet poller saw %s peer(s) with no matching node: %s", len(unmatched), sorted(unmatched))

    touched, confirmed_ids = [], []
    for node in nodes:
        if apply_peer(node, by_code[node.code]):
            touched.append(node.id)
        if node.is_online:
            confirmed_ids.append(node.id)

    touched.extend(sweep_unconfirmed(confirmed_ids))
    notify(touched)

    logger.debug("Fleet poller: %s peers, %s nodes updated", len(peers), len(touched))
