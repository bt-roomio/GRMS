from rest_framework.response import Response
from rest_framework.views import APIView

from main.serializers.knx_from_conf import KnxDeviceFromConfSerializer
from main.swagger.knx_from_conf import knx_from_conf_swagger


class KnxDeviceFromConfListView(APIView):
    @knx_from_conf_swagger()
    def post(self, request):
        serializer = KnxDeviceFromConfSerializer(data=request.data, context={"tenant": request.user.tenant})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
