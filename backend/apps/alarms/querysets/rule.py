from django.db.models import Q

from core.querysets.base_queryset import BaseQuerySet


class AlarmRuleQuerySet(BaseQuerySet):
    SORT_FIELDS = ("alarm_type", "-alarm_type", "created_at", "-created_at")

    def for_tenant(self, tenant_id):
        """Superusers pass ``tenant_id=None`` to reach every tenant's rules."""
        if tenant_id is None:
            return self
        return self.filter(tenant_id=tenant_id)

    def active(self):
        """Rules the evaluator is allowed to run: enabled, on a live profile."""
        return self.filter(enabled=True, device_profile__active=True)

    def for_profiles(self, profile_ids=None):
        if not profile_ids:
            return self
        return self.filter(device_profile_id__in=profile_ids)

    def with_related(self):
        return self.select_related("device_profile")

    def list(
        self,
        tenant_id,
        device_profile=None,
        alarm_type=None,
        enabled=None,
        search_value=None,
        sort_by=None,
    ):
        query = self.for_tenant(tenant_id).with_related()

        if device_profile:
            query = query.filter(device_profile_id=device_profile)

        if alarm_type:
            query = query.filter(alarm_type__in=alarm_type)

        if enabled is not None:
            query = query.filter(enabled=enabled)

        if search_value:
            query = query.filter(
                Q(alarm_type__icontains=search_value) | Q(device_profile__name__icontains=search_value)
            )

        return query.order_by(*sort_by or ["alarm_type"])
