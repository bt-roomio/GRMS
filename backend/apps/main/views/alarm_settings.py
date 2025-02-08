from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from main.models import Tenant
from main.serializers.alarm_settings import AlarmSettingsSerializer
from main.swagger.alarm_settings import AlarmSettingsSwagger


class AlarmSettingsDetailView(APIView):
    @swagger_auto_schema(responses=AlarmSettingsSwagger)
    def get(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        serializer = AlarmSettingsSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(request_body=AlarmSettingsSerializer, responses=AlarmSettingsSwagger)
    def put(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        serializer = AlarmSettingsSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
