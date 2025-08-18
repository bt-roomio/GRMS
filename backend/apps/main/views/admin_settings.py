from rest_framework.views import APIView, Response

from core.utils.perform_request import with_tenant
from core.utils.permission import IsSuperUser, check_perms
from main.models import AdminSettings
from main.serializers.admin_settings import AdminSettingsSerializer
from main.swagger.admin_settings import admin_settings_swagger


class AdminSettingsView(APIView):
    permission_classes = (IsSuperUser,)

    @admin_settings_swagger()
    @check_perms(["main.view_adminsettings"])
    def get(self, _, key):
        instance = AdminSettings.objects.filter(key=key).first()
        serializer = AdminSettingsSerializer(instance)
        return Response(serializer.data)

    @admin_settings_swagger()
    @check_perms(["main.change_adminsettings"])
    def put(self, request, key):
        instance = AdminSettings.objects.filter(key=key).first()
        data = with_tenant(request, key=key)
        serializer = AdminSettingsSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
