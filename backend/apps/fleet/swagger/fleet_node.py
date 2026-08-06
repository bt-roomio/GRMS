from drf_yasg.utils import swagger_auto_schema

from fleet.serializers.fleet_node import (
    FleetNodeCreateSerializer,
    FleetNodeFilterParams,
    FleetNodeSerializer,
    FleetNodeUpdateSerializer,
)
from fleet.swagger.base import NODE_DESCRIPTION, TAG


def list_swagger():
    return swagger_auto_schema(
        query_serializer=FleetNodeFilterParams(),
        responses={200: FleetNodeSerializer(many=True)},
        tags=[TAG],
        operation_description=NODE_DESCRIPTION,
    )


def create_swagger():
    return swagger_auto_schema(
        request_body=FleetNodeCreateSerializer,
        responses={201: FleetNodeSerializer()},
        tags=[TAG],
        operation_description=(
            "Creates a node for one gateway. Send `gateway` (required), optionally `title` "
            "and `description`. The tenant and the `code` are derived from the gateway — "
            "neither is accepted on the wire. Rejected with 400 if the gateway is not a "
            "gateway device, is deactivated, is outside your tenant, or already has an "
            "active node."
        ),
    )


def retrieve_swagger():
    return swagger_auto_schema(responses={200: FleetNodeSerializer()}, tags=[TAG])


def update_swagger():
    return swagger_auto_schema(
        request_body=FleetNodeUpdateSerializer,
        responses={200: FleetNodeSerializer()},
        tags=[TAG],
        operation_description="Only `title` and `description` are editable.",
    )


def delete_swagger():
    return swagger_auto_schema(
        responses={204: "Deactivated"},
        tags=[TAG],
        operation_description=(
            "Soft delete — the row is kept and `is_active` becomes false. The NetBird peer "
            "and setup key are deleted for real, which frees the gateway for a new node."
        ),
    )


def refresh_swagger():
    return swagger_auto_schema(
        request_body=None,
        responses={200: FleetNodeSerializer()},
        tags=[TAG],
        operation_description="Polls NetBird immediately instead of waiting for the next 60s beat tick.",
    )
