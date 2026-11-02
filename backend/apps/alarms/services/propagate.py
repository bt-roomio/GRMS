"""
Alarm propagation.

GRMS deviation: TB writes an ``ALARM``-group row into the polymorphic
``relation`` table. ``shuttle.Relation`` here is device-to-device only, so the
targets are resolved once at creation and stored on the alarm itself
(``propagate_entity_ids``, GIN-indexed). Like TB, they are never recalculated
afterwards — a relation added later does not retroactively widen an old alarm.
"""

from uuid import UUID

from shuttle.models import Relation


def related_device_ids(device_id: UUID, relation_types: list[str] | None) -> set[UUID]:
    """
    Devices on either end of a relation with this one.

    Both directions on purpose: a gateway outage has to be visible on the
    devices behind it, and a device alarm on the gateway in front of it.
    ``Relation`` has no notion of which side is the parent that would let us
    pick one.
    """
    query = Relation.objects.filter(from_id_id=device_id) | Relation.objects.filter(to_id_id=device_id)
    if relation_types:
        query = query.filter(relation_type__in=relation_types)

    ids: set[UUID] = set()
    for from_id, to_id in query.values_list("from_id_id", "to_id_id"):
        ids.add(to_id if from_id == device_id else from_id)

    ids.discard(device_id)
    return ids


def propagation_targets(rule: dict, device_id: UUID, room_id: UUID | None, tenant_id: UUID) -> list[UUID]:
    targets: set[UUID] = set()

    if rule.get("propagate"):
        targets |= related_device_ids(device_id, rule.get("propagateRelationTypes"))

    if rule.get("propagateToOwner") and room_id:
        targets.add(room_id)

    if rule.get("propagateToTenant"):
        targets.add(tenant_id)

    return sorted(targets)
