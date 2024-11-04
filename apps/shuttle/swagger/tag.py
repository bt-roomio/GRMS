from drf_yasg.utils import swagger_auto_schema

from shuttle.serializers.tag import TagFilterParams


def tag_swagger():
    return swagger_auto_schema(
        query_serializer=TagFilterParams(),
        responses={},
        operation_description="""""",
    )
