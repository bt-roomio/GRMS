from drf_yasg.utils import swagger_auto_schema

from shuttle.serializers.attributes import AttributesChangeFilterPath, AttributesChangeSerializer


def swagger_attributes_change():
    return swagger_auto_schema(
        query_serializer=AttributesChangeFilterPath(),
        responses={
            200: AttributesChangeSerializer(many=True),
            404: '{"detail": "Not found!"}',
        },
        operation_description="""
        Change the mass attributes using the specified entity_id and entity. The objects are (Room, type of room, tenant).
        """,
    )
