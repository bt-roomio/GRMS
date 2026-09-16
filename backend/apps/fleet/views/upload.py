import logging

from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView, Response

from core.utils.get_time import get_mil_sec
from core.utils.permission import check_perms
from fleet.models import FleetAuditLog, FleetNode
from fleet.serializers.upload import UploadFileSerializer
from fleet.swagger.upload import upload_swagger
from fleet.utils import sftp
from fleet.utils.audit import client_ip, log_action
from fleet.utils.exceptions import FleetError
from fleet.utils.scope import tenant_scope

logger = logging.getLogger(__name__)

DEFAULT_UPLOAD_MODE = 0o644


class FleetNodeUploadView(APIView):
    parser_classes = (MultiPartParser,)

    @upload_swagger()
    @check_perms(["fleet.upload_fleetnode"])
    def post(self, request, pk):
        node = FleetNode.objects.get_node(pk, tenant_scope(request))
        params = UploadFileSerializer.check(request.data)

        upload = params["file"]
        mode = params.get("mode", DEFAULT_UPLOAD_MODE)

        started = get_mil_sec()
        upload.seek(0)
        try:
            result = sftp.upload_sync(
                node,
                upload,
                upload.name,
                mode=mode,
                overwrite=params["overwrite"],
            )
        except FleetError as exc:
            log_action(
                FleetAuditLog.ACTION.FILE_UPLOAD_FAILED,
                node=node,
                user=request.user,
                detail={"name": upload.name, "error": str(exc)},
                remote_addr=client_ip(request),
            )
            raise ValidationError({"file": str(exc)}) from exc

        log_action(
            FleetAuditLog.ACTION.FILE_UPLOADED,
            node=node,
            user=request.user,
            detail={
                "name": upload.name,
                "duration_ms": get_mil_sec() - started,
                **result,
            },
            remote_addr=client_ip(request),
        )
        return Response(result)
