from rest_framework.response import Response
from rest_framework.views import APIView

from main.serializers.device_from_conf import DeviceFromConfSerializer
from main.swagger.device_from_conf import device_from_conf_swagger


class DeviceFromConfListView(APIView):
    @device_from_conf_swagger()
    def post(self, request):
        serializer = DeviceFromConfSerializer(data=request.data, context={"tenant": request.user.tenant})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
