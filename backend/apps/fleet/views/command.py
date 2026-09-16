import logging

from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView, Response

from core.utils.get_time import get_mil_sec
from core.utils.permission import check_perms
from fleet.models import FleetAuditLog, FleetNode
from fleet.serializers.command import RunCommandSerializer
from fleet.swagger.command import run_command_swagger
from fleet.utils import ssh
from fleet.utils.audit import client_ip, log_action
from fleet.utils.exceptions import FleetError
from fleet.utils.scope import tenant_scope

logger = logging.getLogger(__name__)


class FleetNodeRunCommandView(APIView):
    """
    One command on one node.

    Single-node by design: free-form shell across the fleet belongs to the
    curated action catalog, not here.
    """

    @run_command_swagger()
    @check_perms(["fleet.exec_fleetnode"])
    def post(self, request, pk):
        node = FleetNode.objects.get_node(pk, tenant_scope(request))
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
