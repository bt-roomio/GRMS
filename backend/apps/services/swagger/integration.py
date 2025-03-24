from services.serializers.integration import IntegrationSerializer

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def integration_swagger_list(**kwargs):
    return swagger_auto_schema(
        operation_summary="List Active Integrations",
        operation_description="Retrieve a list of active integrations.",
        responses={200: IntegrationSerializer(many=True)},
        tags=["Services, Integrations"],
        manual_parameters=[
            # If you have query parameters, you can document them as follows:
            openapi.Parameter("page", openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                "size", openapi.IN_QUERY, description="Number of items per page", type=openapi.TYPE_INTEGER
            ),
        ],
    )


def integration_swagger_retrive(**kwargs):
    return swagger_auto_schema(
        operation_summary="Retrieve Active Integrations",
        operation_description="Retrieve the integration details.",
        tags=["Services, Integrations"],
        responses={200: IntegrationSerializer()},
    )


def integration_swagger_update(**kwargs):
    return swagger_auto_schema(
        operation_summary="Update Active Integration",
        operation_description="Update the integration details.",
        tags=["Services, Integrations"],
        request_body=IntegrationSerializer,
        responses={200: IntegrationSerializer()},
    )
