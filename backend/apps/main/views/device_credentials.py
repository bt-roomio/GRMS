from main.models import DeviceCredentials
from main.serializers.device_credentials import DeviceCredentialsSerializer
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView, Response


class DeviceCredentialsDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        instance = get_object_or_404(DeviceCredentials, credentials_id=token)
        serializer = DeviceCredentialsSerializer(instance)
        return Response(serializer.data)
