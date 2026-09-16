"""Turning a request into a job: which nodes, and one task per node."""

from django.db import transaction

from core.utils.get_time import get_mil_sec
from fleet.models import FleetJob, FleetJobTask, FleetNode


def nodes_by_ids(tenant_scope, node_ids):
    """
    Look up the requested nodes inside the caller's scope.

    Returns ``(nodes, missing_ids)``. A node the caller may not see comes back as
    missing rather than being silently dropped — and only ever as *missing*, so
    the answer never confirms that another tenant's node exists.
    """
    node_ids = [str(node_id) for node_id in node_ids or []]
    nodes = list(
        FleetNode.objects.is_active().for_tenant(tenant_scope).filter(id__in=node_ids).select_related("tenant")
    )

    found = {str(node.id) for node in nodes}
    return nodes, [node_id for node_id in node_ids if node_id not in found]


def nodes_for_tenant(tenant_id):
    return list(FleetNode.objects.is_active().for_tenant(tenant_id).select_related("tenant"))


@transaction.atomic
def create_job(*, tenant, action, params, nodes, user) -> FleetJob:
    """
    Create the job and every one of its tasks up front.

    Rows for all targets exist before the runner starts, so the total is known
    the moment the API answers and no node can go missing from the report.
    """
    job = FleetJob.objects.create(
        tenant=tenant,
        action=action,
        params=params or None,
        status=FleetJob.STATUS.PENDING,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )

    FleetJobTask.objects.bulk_create(
        FleetJobTask(
            job=job,
            node=node,
            node_code=node.code,
            status=FleetJobTask.STATUS.PENDING,
            created_by=job.created_by,
        )
        for node in nodes
    )

    return job


def finish(job, status) -> None:
    job.status = status
    job.finished_at = get_mil_sec()
    job.save(update_fields=["status", "finished_at", "updated_at"])
