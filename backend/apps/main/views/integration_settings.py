from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Tenant
from main.serializers.integration_settings import IntegrationSettingsSerializer
from main.swagger.integration_settings import IntegrationSettingsSwagger


class IntegrationSettingsDetailView(APIView):
    @swagger_auto_schema(tags=["Main, IntegrationSettings"], responses=IntegrationSettingsSwagger)
    def get(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        serializer = IntegrationSettingsSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=["Main, IntegrationSettings"],
        request_body=IntegrationSettingsSerializer,
        responses=IntegrationSettingsSwagger,
    )
    def put(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        serializer = IntegrationSettingsSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
