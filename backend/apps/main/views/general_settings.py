import json

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Tenant
from main.serializers.general_settings import GeneralSettingsSerializer


class GeneralSettingsDetailView(APIView):
    def get(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        data = json.loads(str(instance.additional_info)).get('general_settings', {})
        return Response({'tenant_id': instance.id, **data})

    @swagger_auto_schema(request_body=GeneralSettingsSerializer)
    def put(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        serializer = GeneralSettingsSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'tenant_id': instance.id, **serializer.validated_data})
