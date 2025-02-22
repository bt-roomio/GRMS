from drf_yasg.utils import swagger_auto_schema

from shuttle.serializers.relation import RelationSerializer


def relation_swagger(**kwargs):
    return swagger_auto_schema(tags=["Shuttle, Relation"], responses={200: RelationSerializer()}, **kwargs)
