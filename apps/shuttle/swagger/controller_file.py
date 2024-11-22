from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


ControllerFileSwagger = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "controllers": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_STRING),
            description="List of macaddresses. Example: ['11:22:33:44:55:66']",
        ),
        "file": openapi.Schema(
            type=openapi.TYPE_FILE, description="Upload (Firmware, Boot-Defaults, Config, Site-File) file."
        ),
        "file_type": openapi.Schema(type=openapi.TYPE_STRING, description="Type of file"),
    },
)


def controller_file_swagger():
    return swagger_auto_schema(
        request_body=ControllerFileSwagger,
        responses={
            200: '{"message": "Removed [keys]}',
            404: '{"detail": "Not found these keys!"}',
        },
        operation_description="""
        Delete device attributes using provided Device Id, scope and a list of keys. Referencing a non-existing Device Id will cause an error

        Available for users with 'TENANT_ADMIN' or 'CUSTOMER_USER' authority.
        """,
    )
