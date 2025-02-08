from drf_yasg import openapi

from users.serializers.role import PermissionsSerializer

PermissionsSwagger = {
    200: openapi.Response(
        description="Success",
        examples={
            "application/json": [{"id": 1, "name": "Can add log entry", "codename": "add_logentry", "content_type": 1}]
        },
        schema=PermissionsSerializer(many=True),
    ),
}
