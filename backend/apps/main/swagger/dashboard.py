from drf_yasg import openapi

from main.serializers.dashboard import DashboardSerializer

DashboardSwagger = {
    200: openapi.Response(
        description="Success",
        examples={"application/json": {"count": "Count of data.", "results": "Array of data."}},
        schema=DashboardSerializer,
    ),
}

DashboardDetailSwagger = {200: DashboardSerializer}
