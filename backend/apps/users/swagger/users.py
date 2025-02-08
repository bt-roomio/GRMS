from drf_yasg import openapi

from users.serializers.user import UserSerializer

UserSwagger = {
    200: openapi.Response(
        description="Success",
        examples={
            "application/json": {
                "count": "Count of data.",
                "results": [
                    {
                        "id": "UUID",
                        "first_name": "User first name",
                        "last_name": "User last name",
                        "email": "User email is unique",
                        "additional_info": "JSON type data",
                        "phone": "phone",
                        "created_at": "created_at",
                        "tenant_id": "tenant_id",
                        "roles": "roles",
                    }
                ],
            }
        },
        schema=UserSerializer,
    ),
}

UserDetailSwagger = {200: UserSerializer}
