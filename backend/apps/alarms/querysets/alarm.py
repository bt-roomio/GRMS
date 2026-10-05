from django.db.models import Q

from alarms.constants import AlarmStatus
from core.querysets.base_queryset import BaseQuerySet


class AlarmQuerySet(BaseQuerySet):
    def active(self):
        return self.filter(cleared=False)

    def for_tenant(self, tenant_id):
        """Superusers pass ``tenant_id=None`` to see every tenant."""
        if tenant_id is None:
            return self
        return self.filter(tenant_id=tenant_id)

    def for_device(self, device_id):
        """
        Alarms of a device: the ones it raised plus the ones propagated onto it
        (a gateway outage shows up on every device behind it).
        """
        return self.filter(Q(originator_id=device_id) | Q(propagate_entity_ids__contains=[device_id]))

    def with_related(self):
        return self.select_related("originator", "room", "tenant", "assignee")

    def list(
        self,
        tenant_id,
        types=None,
        severities=None,
        status=None,
        device_id=None,
        room_id=None,
        assignee_id=None,
        date_from=None,
        date_to=None,
        search_value=None,
        sort_by=None,
    ):
        query = self.for_tenant(tenant_id).with_related()

        if types:
            query = query.filter(alarm_type__in=types)

        if severities:
            query = query.filter(severity__in=severities)

        if status:
            query = query.filter(**self.status_filter(status))

        if device_id:
            query = query.for_device(device_id)

        if room_id:
            query = query.filter(room_id=room_id)

        if assignee_id:
            # "unassigned" is a first-class filter in TB's table, so the sentinel
            # has to mean something other than "no filter".
            query = (
                query.filter(assignee__isnull=True) if assignee_id == "none" else query.filter(assignee_id=assignee_id)
            )

        if date_from:
            query = query.filter(start_ts__gte=date_from)

        if date_to:
            query = query.filter(start_ts__lte=date_to)

        if search_value:
            query = query.filter(
                Q(alarm_type__icontains=search_value)
                | Q(originator__name__icontains=search_value)
                | Q(room__number__icontains=search_value)
            )

        return query.order_by(*sort_by or ["-start_ts"])

    @staticmethod
    def status_filter(status) -> dict:
        return {
            "ACTIVE": {"cleared": False},
            "CLEARED": {"cleared": True},
            "UNACK": {"acknowledged": False},
            "ACK": {"acknowledged": True},
            AlarmStatus.ACTIVE_UNACK: {"cleared": False, "acknowledged": False},
            AlarmStatus.ACTIVE_ACK: {"cleared": False, "acknowledged": True},
            AlarmStatus.CLEARED_UNACK: {"cleared": True, "acknowledged": False},
            AlarmStatus.CLEARED_ACK: {"cleared": True, "acknowledged": True},
        }[status]
