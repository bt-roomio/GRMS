from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.permission import check_perms
from main.models import Tenant
from main.serializers.alarm_settings import AlarmSettingsSerializer
from main.swagger.alarm_settings import alarm_settings_swagger


class AlarmSettingsDetailView(APIView):
    @alarm_settings_swagger()
    @check_perms(["main.view_alarmsettings"])
    def get(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        serializer = AlarmSettingsSerializer(instance)
        return Response(serializer.data)

    @alarm_settings_swagger()
    @check_perms(["main.view_alarmsettings"])
    def put(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        serializer = AlarmSettingsSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
