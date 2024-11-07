from drf_yasg import openapi
from drf_yasg.openapi import Schema
from drf_yasg.utils import swagger_auto_schema


def controller_status_swagger():
    return swagger_auto_schema(
        responses={
            200: Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "status": Schema(type=openapi.TYPE_BOOLEAN),
                    "count": Schema(type=openapi.TYPE_INTEGER),
                },
            ),
        },
        operation_description="""Get the status of controllers.""",
    )
