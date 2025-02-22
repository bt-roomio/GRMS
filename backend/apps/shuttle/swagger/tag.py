from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from shuttle.serializers.tag import TagFilterParams

response_200 = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "data": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "attribute_name": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=[openapi.Schema(type=openapi.TYPE_INTEGER), openapi.Schema(type=openapi.TYPE_BOOLEAN)],
                    ),
                )
            },
        ),
        "latestValues": openapi.Schema(
            type=openapi.TYPE_OBJECT, properties={"attribute_name": openapi.Schema(type=openapi.TYPE_INTEGER)}
        ),
    },
)


def tag_swagger():
    return swagger_auto_schema(
        tags=["Shuttle, Tag"],
        query_serializer=TagFilterParams(),
        responses={200: response_200},
        operation_description="""""",
    )
