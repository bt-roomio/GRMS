import logging

from django.conf import settings
from django.db import transaction

from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView, Response

from core.utils.get_time import get_mil_sec
from core.utils.pagination import pagination
from core.utils.permission import check_perms
from fleet.actions import catalog
from fleet.models import FleetAuditLog, FleetJob, FleetJobTask
from fleet.serializers.job import (
    FleetJobCreateSerializer,
    FleetJobDetailSerializer,
    FleetJobFilterParams,
    FleetJobSerializer,
)
from fleet.swagger.job import (
    action_catalog_swagger,
    job_cancel_swagger,
    job_create_swagger,
    job_list_swagger,
    job_retrieve_swagger,
)
from fleet.utils.audit import client_ip, log_action
from fleet.utils.job import create_job, nodes_by_ids, nodes_for_tenant
from fleet.utils.scope import tenant_scope
from main.models import Tenant

logger = logging.getLogger(__name__)


def _resolve_targets(request, params):
    """
    Settle *which tenant* and *which nodes* before anything is written.

    A job belongs to exactly one tenant. For a tenant user their own scope
    settles it. A superuser may target anything, so they either name the tenant
    or let a single-tenant selection of nodes name it — a selection spanning two
    tenants is refused rather than silently split.
    """
    scope = tenant_scope(request)
    asked = params.get("tenant")

    if scope is not None and asked is not None and str(asked) != str(scope):
        # Same answer as an unknown tenant — never confirm a foreign one exists.
        raise ValidationError({"tenant": "Unknown tenant."})

    if params["all_nodes"]:
        tenant_id = asked or scope
        if tenant_id is None:
            raise ValidationError({"tenant": "`all_nodes` needs a `tenant` — the whole fleet is more than one."})

        tenant = Tenant.objects.filter(id=tenant_id).first()
        if tenant is None:
            raise ValidationError({"tenant": "Unknown tenant."})
        return tenant, nodes_for_tenant(tenant.id)

    nodes, missing = nodes_by_ids(scope, params.get("node_ids"))
    if missing:
        raise ValidationError({"node_ids": f"Unknown node(s): {', '.join(missing)}"})

    tenant_ids = {node.tenant_id for node in nodes}
    if len(tenant_ids) > 1:
        raise ValidationError({"node_ids": "All nodes in one job must belong to the same tenant."})

    tenant = nodes[0].tenant
    if asked is not None and str(asked) != str(tenant.id):
        raise ValidationError({"tenant": "The selected nodes belong to a different tenant."})
    return tenant, nodes


class FleetJobListView(APIView):
    @job_list_swagger()
    @check_perms(["fleet.view_fleetjob"])
    def get(self, request):
        params = FleetJobFilterParams.check(request.GET)
        queryset = FleetJob.objects.list(
            tenant_id=tenant_scope(request),
            sort_by=params.get("sort_by", []),
            status=params.get("status"),
            action=params.get("action"),
        ).with_counts()
        serializer = FleetJobSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)

    @job_create_swagger()
    @check_perms(["fleet.run_fleetjob"])
    def post(self, request):
        params = FleetJobCreateSerializer.check(request.data)

        tenant, nodes = _resolve_targets(request, params)
        if not nodes:
            raise ValidationError({"node_ids": "No active nodes to run this on."})

        if len(nodes) > settings.FLEET_JOB_MAX_NODES:
            raise ValidationError(
                {"node_ids": f"A job may target at most {settings.FLEET_JOB_MAX_NODES} nodes — got {len(nodes)}."}
            )

        job = create_job(
            tenant=tenant,
            action=params["action"],
            params=params.get("params"),
            nodes=nodes,
            user=request.user,
        )

        log_action(
            FleetAuditLog.ACTION.JOB_STARTED,
            user=request.user,
            detail={
                "job_id": str(job.id),
                "action": job.action,
                "params": job.params,
                "nodes": [node.code for node in nodes],
            },
            remote_addr=client_ip(request),
        )

        # After commit: the worker must not look for a job the request has not
        # written yet.
        transaction.on_commit(lambda: _dispatch(job.id))

        job = FleetJob.objects.with_counts().with_tasks().get(pk=job.id)
        return Response(FleetJobDetailSerializer(job).data, 201)


def _dispatch(job_id) -> None:
    from fleet.tasks import run_fleet_job

    run_fleet_job.delay(str(job_id))


class FleetJobDetailView(APIView):
    @job_retrieve_swagger()
    @check_perms(["fleet.view_fleetjob"])
    def get(self, request, pk):
        job = FleetJob.objects.with_counts().with_tasks().get_job(pk, tenant_scope(request))
        return Response(FleetJobDetailSerializer(job).data)


class FleetJobCancelView(APIView):
    """
    The kill switch.

    Nothing is killed mid-flight: a node already being talked to finishes and
    records its result. Everything not yet started is marked cancelled, and the
    runner checks the job's status before it opens each remaining connection.
    """

    @job_cancel_swagger()
    @check_perms(["fleet.run_fleetjob"])
    def post(self, request, pk):
        job = FleetJob.objects.get_job(pk, tenant_scope(request))

        if job.status in (FleetJob.STATUS.DONE, FleetJob.STATUS.CANCELLED):
            raise ValidationError({"status": f"This job is already {job.status}."})

        was_pending = job.status == FleetJob.STATUS.PENDING

        job.status = FleetJob.STATUS.CANCELLED
        # A running job still has connections open; the runner writes the real
        # finish time when the last of them returns.
        if was_pending:
            job.finished_at = get_mil_sec()
        job.updated_by = request.user
        job.save(update_fields=["status", "finished_at", "updated_by", "updated_at"])

        job.tasks.filter(status=FleetJobTask.STATUS.PENDING).update(
            status=FleetJobTask.STATUS.CANCELLED,
            finished_at=get_mil_sec(),
        )

        log_action(
            FleetAuditLog.ACTION.JOB_CANCELLED,
            user=request.user,
            detail={"job_id": str(job.id), "action": job.action},
            remote_addr=client_ip(request),
        )

        job = FleetJob.objects.with_counts().with_tasks().get(pk=job.id)
        return Response(FleetJobDetailSerializer(job).data)


class FleetActionCatalogView(APIView):
    """The menu. The UI builds itself from this instead of hardcoding commands."""

    @action_catalog_swagger()
    @check_perms(["fleet.view_fleetjob"])
    def get(self, request):
        return Response({"results": catalog()})
