import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView, Response

from main.models import DeviceCredentials
from main.serializers.device_credentials import DeviceCredentialsDetailSerializer

logger = logging.getLogger(__name__)


class DeviceCredentialsDetailView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=["Main, Device Credentials"])
    def get(self, request, token):
        logger.debug("Fetching device credentials for token: %s", token)
        instance = get_object_or_404(DeviceCredentials, credentials_id=token)
        serializer = DeviceCredentialsDetailSerializer(instance)
        logger.debug("Device credentials retrieved: %s", serializer.data)
        return Response(serializer.data)
