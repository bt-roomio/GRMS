from drf_yasg.utils import swagger_auto_schema

from fleet.serializers.enrollment import InstallCommandSerializer
from fleet.swagger.base import TAG


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
