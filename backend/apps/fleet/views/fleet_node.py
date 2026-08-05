import logging

from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from fleet.models import FleetNode
from fleet.netbird.exceptions import NetBirdError
from fleet.serializers.fleet_node import (
    FleetNodeCreateSerializer,
    FleetNodeFilterParams,
    FleetNodeSerializer,
    FleetNodeUpdateSerializer,
)
from fleet.swagger.fleet_node import (
    create_swagger,
    delete_swagger,
    list_swagger,
    refresh_swagger,
    retrieve_swagger,
    update_swagger,
)
from fleet.utils.enroll import release_peer
from fleet.utils.scope import tenant_scope

logger = logging.getLogger(__name__)


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
            node_id=params.get("id"),
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
        return Response(FleetNodeSerializer(FleetNode.objects.get_node(pk, tenant_scope(request))).data)

    @update_swagger()
    @check_perms(["fleet.change_fleetnode"])
    def put(self, request, pk):
        node = FleetNode.objects.get_node(pk, tenant_scope(request))
        serializer = FleetNodeUpdateSerializer(node, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(FleetNodeSerializer(node).data)

    @delete_swagger()
    @check_perms(["fleet.delete_fleetnode"])
    def delete(self, request, pk):
        node = FleetNode.objects.get_node(pk, tenant_scope(request))

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


class FleetNodeStatusView(APIView):
    """Force a poll instead of waiting for the next beat tick."""

    @refresh_swagger()
    @check_perms(["fleet.view_fleetnode"])
    def post(self, request, pk):
        from fleet.tasks import poll_fleet_peers

        node = FleetNode.objects.get_node(pk, tenant_scope(request))
        try:
            poll_fleet_peers()
        except NetBirdError as exc:
            raise ValidationError({"netbird": str(exc)}) from exc

        node.refresh_from_db()
        return Response(FleetNodeSerializer(node).data)
