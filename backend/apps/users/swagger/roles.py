from drf_yasg import openapi

from users.serializers.role import RoleSerializer

RolesSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": [{"id": 1, "name": "SYS_ADMIN", "permissions": []}]},
        schema=RoleSerializer(many=True),
    ),
}


RoleDetailSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"id": 1, "name": "SYS_ADMIN", "permissions": []}},
        schema=RoleSerializer,
    ),
}
