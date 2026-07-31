import logging

from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.get_time import get_mil_sec
from core.utils.pagination import pagination
from core.utils.permission import check_perms
from fleet import ssh
from fleet.enroll import (
    EnrollmentError,
    install_command,
    install_url,
    prepare_enrollment,
    release_peer,
)
from fleet.exceptions import FleetError
from fleet.models import FleetAuditLog, FleetNode
from fleet.netbird.exceptions import NetBirdError
from fleet.serializers.fleet_node import (
    FleetAuditLogFilterParams,
    FleetAuditLogSerializer,
    FleetNodeCreateSerializer,
    FleetNodeFilterParams,
    FleetNodeSerializer,
    FleetNodeUpdateSerializer,
    RunCommandSerializer,
)
from fleet.swagger.fleet_node import (
    audit_log_swagger,
    create_swagger,
    delete_swagger,
    install_swagger,
    list_swagger,
    refresh_swagger,
    retrieve_swagger,
    run_command_swagger,
    update_swagger,
)
from fleet.utils.audit import client_ip, log_action
from fleet.utils.scope import tenant_scope

logger = logging.getLogger(__name__)


def get_node(request, pk):
    return get_object_or_404(FleetNode.objects.is_active().for_tenant(tenant_scope(request)), pk=pk)


class FleetNodeListView(APIView):
    @list_swagger()
    @check_perms(["fleet.view_fleetnode"])
    def get(self, request):
        params = FleetNodeFilterParams.check(request.GET)
        queryset = FleetNode.objects.list(
            tenant_id=tenant_scope(request),
            sort_by=params.get("sort_by", []),
            search_value=params.get("search_value"),
            is_online=params.get("is_online"),
        )
        serializer = FleetNodeSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)

    @create_swagger()
    @check_perms(["fleet.add_fleetnode"])
    def post(self, request):
        serializer = FleetNodeCreateSerializer(
            data=request.data,
            context={"tenant_scope": tenant_scope(request)},
        )
        serializer.is_valid(raise_exception=True)
        node = serializer.save(created_by=request.user)
        return Response(FleetNodeSerializer(node).data, 201)


class FleetNodeDetailView(APIView):
    @retrieve_swagger()
    @check_perms(["fleet.view_fleetnode"])
    def get(self, request, pk):
        return Response(FleetNodeSerializer(get_node(request, pk)).data)

    @update_swagger()
    @check_perms(["fleet.change_fleetnode"])
    def put(self, request, pk):
        node = get_node(request, pk)
        serializer = FleetNodeUpdateSerializer(node, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(FleetNodeSerializer(node).data)

    @delete_swagger()
    @check_perms(["fleet.delete_fleetnode"])
    def delete(self, request, pk):
        node = get_node(request, pk)

        # Release the peer before hiding the row, or NetBird keeps a live peer
        # for a gateway that is about to be free for a new node to claim.
        try:
            release_peer(node, user=request.user)
        except NetBirdError:
            logger.exception("Could not release the NetBird peer for %s", node.code)
            raise ValidationError(
                {"netbird": "Could not delete this node's NetBird peer. Try again once NetBird is reachable."}
            ) from None

        node.is_active = False
        node.updated_by = request.user
        node.save(update_fields=["is_active", "updated_by", "updated_at"])
        return Response({}, 204)


class FleetNodeInstallView(APIView):
    """
    Everything behind the "Install agent" button.

    Whatever the node had before, it comes out with exactly one unused
    single-use setup key and no peer.
    """

    @install_swagger()
    @check_perms(["fleet.enroll_fleetnode"])
    def post(self, request, pk):
        node = get_node(request, pk)
        replaced = bool(node.netbird_peer_id or node.netbird_setup_key_id)

        try:
            # The key never leaves the server; it is rendered into the script
            # when the install link is fetched.
            prepare_enrollment(node, user=request.user)
        except NetBirdError as exc:
            logger.exception("Could not prepare enrollment for %s", node.code)
            raise ValidationError({"netbird": str(exc)}) from exc
        except EnrollmentError as exc:
            raise ValidationError({"netbird": str(exc)}) from exc

        return Response(
            {
                "install_url": install_url(node, request),
                "command": install_command(node, request),
                "hostname": node.code,
                "peer_replaced": replaced,
                "expires_at": node.token_expires_at,
            }
        )


class FleetNodeRunCommandView(APIView):
    """
    One command on one node.

    Single-node by design: free-form shell across the fleet belongs to the
    curated action catalog, not here.
    """

    @run_command_swagger()
    @check_perms(["fleet.exec_fleetnode"])
    def post(self, request, pk):
        node = get_node(request, pk)
        params = RunCommandSerializer.check(request.data)
        command = params["command"]

        started = get_mil_sec()
        try:
            result = ssh.run_command_sync(node, command, timeout=params.get("timeout"))
        except FleetError as exc:
            log_action(
                FleetAuditLog.ACTION.COMMAND_RUN,
                node=node,
                user=request.user,
                detail={"command": command, "error": str(exc)},
                remote_addr=client_ip(request),
            )
            raise ValidationError({"command": str(exc)}) from exc

        log_action(
            FleetAuditLog.ACTION.COMMAND_RUN,
            node=node,
            user=request.user,
            detail={
                "command": command,
                "rc": result["rc"],
                "duration_ms": get_mil_sec() - started,
            },
            remote_addr=client_ip(request),
        )
        return Response(result)


class FleetNodeAuditLogView(APIView):
    @audit_log_swagger()
    @check_perms(["fleet.view_fleetnode"])
    def get(self, request, pk):
        node = get_node(request, pk)
        params = FleetAuditLogFilterParams.check(request.GET)

        queryset = FleetAuditLog.objects.for_node(node.id)
        if params.get("action"):
            queryset = queryset.filter(action=params["action"])

        serializer = FleetAuditLogSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)


class FleetNodeStatusView(APIView):
    """Force a poll instead of waiting for the next beat tick."""

    @refresh_swagger()
    @check_perms(["fleet.view_fleetnode"])
    def post(self, request, pk):
        from fleet.tasks import poll_fleet_peers

        node = get_node(request, pk)
        try:
            poll_fleet_peers()
        except NetBirdError as exc:
            raise ValidationError({"netbird": str(exc)}) from exc

        node.refresh_from_db()
        return Response(FleetNodeSerializer(node).data)
