from drf_yasg.utils import swagger_auto_schema

from fleet.serializers.job import (
    FleetJobCreateSerializer,
    FleetJobDetailSerializer,
    FleetJobFilterParams,
    FleetJobSerializer,
)
from fleet.swagger.base import JOB_DESCRIPTION, TAG


def job_list_swagger():
    return swagger_auto_schema(
        query_serializer=FleetJobFilterParams(),
        responses={200: FleetJobSerializer(many=True)},
        tags=[TAG],
        operation_description=JOB_DESCRIPTION,
    )


def job_create_swagger():
    return swagger_auto_schema(
        request_body=FleetJobCreateSerializer,
        responses={201: FleetJobDetailSerializer()},
        tags=[TAG],
        operation_description=(
            "Runs one catalog action across many nodes.\n\n"
            "Send `action` (a key from `GET /fleet/actions/`), optional `params`, and the "
            "targets as either `node_ids` (a list) or `all_nodes: true` — exactly one of the "
            "two. Every targeted node gets a task row immediately, so the response already "
            "carries the full list; poll `GET /fleet/jobs/{id}/` for results.\n\n"
            "400 if the action is unknown, a param is not one the action accepts, any id in "
            "`node_ids` is unknown *or outside your tenant*, the selection spans two tenants, "
            "or it exceeds `FLEET_JOB_MAX_NODES`. Nothing is run when any target is rejected."
        ),
    )


def job_retrieve_swagger():
    return swagger_auto_schema(
        responses={200: FleetJobDetailSerializer()},
        tags=[TAG],
        operation_description="The job with one task per targeted node. This is the polling endpoint.",
    )


def job_cancel_swagger():
    return swagger_auto_schema(
        request_body=None,
        responses={200: FleetJobDetailSerializer()},
        tags=[TAG],
        operation_description=(
            "Stops the job from reaching any node it has not started on yet. A node already "
            "being talked to finishes and records its result — nothing is killed mid-command."
        ),
    )


def action_catalog_swagger():
    return swagger_auto_schema(
        responses={200: '{"results": [{"name": "command", "title": "...", "params": []}]}'},
        tags=[TAG],
        operation_description=(
            "The action catalog a job may draw from. Build the UI menu from this — the "
            "command behind each entry lives on the server and is never sent by the client."
        ),
    )
