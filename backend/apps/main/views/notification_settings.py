from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.permission import check_perms
from main.models import Tenant
from main.serializers.notification_settings import NotificationSettingsSerializer
from main.swagger.notification_settings import (
    notification_settings_swagger,
    notification_settings_update_swagger,
)


class NotificationSettingsDetailView(APIView):
    @notification_settings_swagger()
    @check_perms(["main.view_notificationsettings"])
    def get(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        return Response(NotificationSettingsSerializer(instance).data)

    @notification_settings_update_swagger()
    @check_perms(["main.change_notificationsettings"])
    def put(self, request):
        instance = get_object_or_404(Tenant, id=request.user.tenant_id)
        serializer = NotificationSettingsSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)
