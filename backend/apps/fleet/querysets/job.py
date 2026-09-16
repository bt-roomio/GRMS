from django.apps import apps
from django.db.models import Count, Q

from rest_framework.generics import get_object_or_404

from core.querysets.base_queryset import BaseQuerySet


class FleetJobQuerySet(BaseQuerySet):
    def for_tenant(self, tenant_id):
        """Superusers pass ``tenant_id=None`` to see the whole fleet."""
        if tenant_id is None:
            return self
        return self.filter(tenant_id=tenant_id)

    def list(self, tenant_id, sort_by=None, status=None, action=None):
        query = self.for_tenant(tenant_id).select_related("tenant", "created_by")

        if status:
            query = query.filter(status=status)

        if action:
            query = query.filter(action=action)

        return query.order_by(*sort_by or ["-created_at"])

    def get_job(self, job_id, tenant_id):
        return get_object_or_404(self.for_tenant(tenant_id), pk=job_id)

    def with_tasks(self):
        return self.prefetch_related("tasks__node")

    def with_counts(self):
        """Per-status task tallies, so a list of jobs stays one query."""
        statuses = apps.get_model("fleet", "FleetJobTask").STATUS.values
        return self.annotate(
            task_total=Count("tasks"),
            **{f"task_{status}": Count("tasks", filter=Q(tasks__status=status)) for status in statuses},
        )


class FleetJobTaskQuerySet(BaseQuerySet):
    def for_job(self, job_id):
        return self.filter(job_id=job_id).select_related("node")

    def unfinished(self):
        return self.filter(status__in=(self.model.STATUS.PENDING, self.model.STATUS.RUNNING))
