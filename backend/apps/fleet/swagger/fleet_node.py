from drf_yasg.utils import swagger_auto_schema

from fleet.serializers.fleet_node import (
    FleetAuditLogFilterParams,
    FleetAuditLogSerializer,
    FleetNodeCreateSerializer,
    FleetNodeFilterParams,
    FleetNodeSerializer,
    FleetNodeUpdateSerializer,
    InstallCommandSerializer,
    RunCommandSerializer,
    UploadFileSerializer,
    UploadResultSerializer,
)

TAG = "Fleet"

NODE_DESCRIPTION = """
**A `FleetNode` is the VM that hosts one gateway.**

Exactly one active node per gateway, so the gateway is the node's identity: it
decides the tenant, and it decides `code`, which is generated as
`{tenant_name}_{gateway_name}` and used verbatim as the NetBird peer name.

A node is reachable only over the NetBird mesh, and `is_online` reflects mesh
connectivity — not application health.

Nearly every field is assigned by the system, never sent by the client:
`mesh_ip` / `is_online` / `last_seen` / `os` / `netbird_version` come from the
NetBird poller, and `ssh_user` comes from settings.
"""


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


def install_swagger():
    return swagger_auto_schema(
        request_body=None,
        responses={200: InstallCommandSerializer()},
        tags=[TAG],
        operation_description=(
            "Prepares the node for enrollment and returns the install instructions. "
            "Any existing peer **and** its setup key are deleted first — used or unused — "
            "then a fresh single-use key is minted and a new one-time link issued, so the "
            "gateway always ends up with exactly one active peer under the same "
            "`{tenant}_{gateway}` name. Any previously issued link stops working.\n\n"
            "`command` is `curl … | sudo bash`, so `FLEET_INSTALL_BASE_URL` must be a URL the "
            "VM can actually reach. It runs the whole bootstrap as root in one process — "
            "never run the script line by line, since half of it needs root and "
            "`sudo cmd > file` cannot write as root (the redirect is done by your own shell).\n\n"
            "Re-running it on an already-enrolled node is how you re-enrol."
        ),
    )


def run_command_swagger():
    return swagger_auto_schema(
        request_body=RunCommandSerializer,
        responses={200: '{"rc": 0, "stdout": "...", "stderr": ""}'},
        tags=[TAG],
        operation_description="Runs a single command on the node over SSH and returns rc/stdout/stderr.",
    )


def upload_swagger():
    return swagger_auto_schema(
        request_body=UploadFileSerializer,
        responses={200: UploadResultSerializer()},
        tags=[TAG],
        operation_description=(
            "Uploads one file to the node over SFTP. Attach the file — that is the whole request.\n\n"
            "It lands in the node's upload root under its own name: by default the agent's home "
            "directory, the same place the browser terminal opens in. Any directory part in the "
            "filename is stripped, and symlinks pointing outside the root are refused before "
            "anything is written. The file is staged under a temporary name and renamed into "
            "place, so a failed transfer never leaves a partial file."
        ),
    )


def refresh_swagger():
    return swagger_auto_schema(
        request_body=None,
        responses={200: FleetNodeSerializer()},
        tags=[TAG],
        operation_description="Polls NetBird immediately instead of waiting for the next 60s beat tick.",
    )


def audit_log_swagger():
    return swagger_auto_schema(
        query_serializer=FleetAuditLogFilterParams(),
        responses={200: FleetAuditLogSerializer(many=True)},
        tags=[TAG],
    )
