from drf_yasg.utils import swagger_auto_schema

from fleet.serializers.command import RunCommandSerializer
from fleet.swagger.base import TAG


def run_command_swagger():
    return swagger_auto_schema(
        request_body=RunCommandSerializer,
        responses={200: '{"rc": 0, "stdout": "...", "stderr": ""}'},
        tags=[TAG],
        operation_description="Runs a single command on the node over SSH and returns rc/stdout/stderr.",
    )
