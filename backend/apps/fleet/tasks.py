import logging

from celery import shared_task
from django.conf import settings

from core.utils.get_time import get_mil_sec
from fleet.models import FleetAuditLog, FleetNode
from fleet.netbird.client import NetBirdClient
from fleet.netbird.exceptions import NetBirdError, NetBirdNotConfigured
from fleet.observables.fleet_node import publish_fleet_nodes
from fleet.utils.audit import log_action
from fleet.utils.time import to_mil_sec

logger = logging.getLogger(__name__)


def peer_name(peer) -> str:
    return peer.get("name") or ""


def apply_peer(node: FleetNode, peer: dict) -> bool:
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

    The only fleet write that does not go through ``save()``: ``QuerySet.update()``
    is straight SQL, so no ``post_save`` fires and the repaint is published by hand.
    """
    stale = FleetNode.objects.is_active().filter(is_online=True).exclude(id__in=confirmed_ids)
    rows = list(stale.values_list("id", "tenant_id"))
    stale.update(is_online=False, updated_at=get_mil_sec())

    publish_fleet_nodes(tenant_id for _, tenant_id in rows)
    return [node_id for node_id, _ in rows]


@shared_task(name="fleet.tasks.poll_fleet_peers", ignore_result=True)
def poll_fleet_peers():
    try:
        client = NetBirdClient()
    except NetBirdNotConfigured:
        logger.debug("Fleet poller skipped: NetBird is not configured")
        return

    try:
        peers = client.list_peers(group_id=settings.NETBIRD_HOTEL_GROUP_ID or None)
    except NetBirdError:
        logger.exception("Fleet poller could not reach the NetBird API — leaving node status untouched")
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

    logger.debug("Fleet poller: %s peers, %s nodes updated", len(peers), len(touched))
