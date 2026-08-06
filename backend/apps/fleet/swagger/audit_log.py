from drf_yasg.utils import swagger_auto_schema

from fleet.serializers.audit_log import FleetAuditLogFilterParams, FleetAuditLogSerializer
from fleet.swagger.base import TAG


def audit_log_swagger():
    return swagger_auto_schema(
        query_serializer=FleetAuditLogFilterParams(),
        responses={200: FleetAuditLogSerializer(many=True)},
        tags=[TAG],
    )
