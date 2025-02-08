from drf_yasg.utils import swagger_auto_schema

from shuttle.serializers.relation import RelationFilterParams, RelationSerializer


def relation_swagger():
    return swagger_auto_schema(
        query_serializer=RelationFilterParams(),
        responses={200: RelationSerializer()},
    )
