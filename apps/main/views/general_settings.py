import json

from drf_yasg.utils import swagger_auto_schema
from main.models import Tenant
from main.serializers.general_settings import GeneralSettingsSerializer
from main.swagger.general_settings import GeneralSettingsSwagger
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView


class GeneralSettingsDetailView(APIView):
    @swagger_auto_schema(responses=GeneralSettingsSwagger)
    def get(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        data = json.loads(instance.additional_info or "{}").get("general_settings", {})
        serializer = GeneralSettingsSerializer(instance, data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @swagger_auto_schema(request_body=GeneralSettingsSerializer, responses=GeneralSettingsSwagger)
    def put(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        serializer = GeneralSettingsSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
