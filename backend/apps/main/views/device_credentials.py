from drf_yasg.utils import swagger_auto_schema

from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView, Response

from core.utils.permission import check_perms
from main.models import DeviceCredentials
from main.serializers.device_credentials import DeviceCredentialsDetailSerializer


class DeviceCredentialsDetailView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=["Main, Device Credentials"])
    @check_perms(["main.view_devicecredentials"])
    def get(self, request, token):
        instance = get_object_or_404(DeviceCredentials, credentials_id=token)
        serializer = DeviceCredentialsDetailSerializer(instance)
        return Response(serializer.data)
