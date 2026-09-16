from drf_yasg.utils import swagger_auto_schema

from fleet.serializers.upload import UploadFileSerializer, UploadResultSerializer
from fleet.swagger.base import TAG


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
