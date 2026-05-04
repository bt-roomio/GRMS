from drf_yasg.utils import swagger_auto_schema

from services.serializers.integration import IntegrationParams, IntegrationSerializer


def integration_swagger_list(**kwargs):
    return swagger_auto_schema(
        operation_summary="List Active Integrations",
        operation_description="Retrieve a list of active integrations.",
        responses={200: IntegrationSerializer(many=True)},
        tags=["Services, Integrations"],
        query_serializer=IntegrationParams,
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
