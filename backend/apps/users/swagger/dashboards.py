from drf_yasg import openapi

from main.serializers.dashboard import SimpleDashboardSerializer
from users.serializers.dashboard import UserDashboardSerializer

UserDashboardSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
        schema=UserDashboardSerializer,
    ),
}

UserDashboardDetailSwagger = {200: UserDashboardSerializer}

MyDashboardsSwagger = {200: SimpleDashboardSerializer(many=True)}
