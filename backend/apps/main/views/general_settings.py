from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from main.models import Tenant
from main.serializers.general_settings import GeneralSettingsSerializer
from main.swagger.general_settings import GeneralSettingsSwagger


class GeneralSettingsDetailView(APIView):
    @swagger_auto_schema(tags=["Main, GeneralSettings"], responses=GeneralSettingsSwagger)
    @check_perms(["main.view_generalsettings"])
    def get(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        serializer = GeneralSettingsSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=["Main, GeneralSettings"],
        request_body=GeneralSettingsSerializer,
        responses=GeneralSettingsSwagger,
    )
    @check_perms(["main.change_generalsettings"])
    def put(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        serializer = GeneralSettingsSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)
