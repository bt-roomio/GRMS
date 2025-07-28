from django.contrib.auth.models import Permission

from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from users.serializers.role import PermissionsSerializer
from users.swagger.permissions import PermissionsSwagger

HIDDEN_PERMS = [
    "session",
    "customer",
    "logentry",
    "taskresult",
    "groupresult",
    "contenttype",
    "chordcounter",
    "periodictask",
    "periodictasks",
    "tskvdictionary",
    "solarschedule",
    "clockedschedule",
    "crontabschedule",
    "intervalschedule",
    "devicecredentials",
]


class PermissionsListView(APIView):
    @swagger_auto_schema(tags=["Users, Permissions"], responses=PermissionsSwagger)
    @check_perms(["users.view_permissions"])
    def get(self, request):
        instance = Permission.objects.exclude(content_type__model__in=HIDDEN_PERMS).order_by("id")
        serializer = PermissionsSerializer(instance, many=True)
        return Response(serializer.data)
