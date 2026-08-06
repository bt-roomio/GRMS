from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from fleet.models import FleetAuditLog, FleetNode
from fleet.serializers.audit_log import FleetAuditLogFilterParams, FleetAuditLogSerializer
from fleet.swagger.audit_log import audit_log_swagger
from fleet.utils.scope import tenant_scope


class FleetNodeAuditLogView(APIView):
    @audit_log_swagger()
    @check_perms(["fleet.view_fleetnode"])
    def get(self, request, pk):
        node = FleetNode.objects.get_node(pk, tenant_scope(request))
        params = FleetAuditLogFilterParams.check(request.GET)

        queryset = FleetAuditLog.objects.for_node(node.id)
        if params.get("action"):
            queryset = queryset.filter(action=params["action"])

        serializer = FleetAuditLogSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)
