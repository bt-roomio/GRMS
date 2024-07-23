from drf_yasg import openapi

from users.serializers.group import GroupSerializer

GroupsSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": [{"id": 1, "name": "SYS_ADMIN", "permissions": []}]},
        schema=GroupSerializer(many=True),
    ),
}


GroupDetailSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"id": 1, "name": "SYS_ADMIN", "permissions": []}},
        schema=GroupSerializer,
    ),
}
