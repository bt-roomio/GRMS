from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from shuttle.serializers.controller_file import ControllerFileSerializer
from shuttle.swagger.controller_file import ControllerFileSwagger, ControllerFileResponseSwagger


class ControllerFileListView(APIView):
    @swagger_auto_schema(request_body=ControllerFileSwagger, responses={200: ControllerFileResponseSwagger})
    def post(self, request):
        serializer = ControllerFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user, tenant_id=request.user.tenant_id)
        return Response(serializer.data)
