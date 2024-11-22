from rest_framework.response import Response
from rest_framework.views import APIView

from shuttle.serializers.controller_file import ControllerSerializer
from shuttle.swagger.controller_file import (
    controller_file_swagger,
)


class ControllerFileListView(APIView):
    @controller_file_swagger()
    def post(self, request):
        serializer = ControllerSerializer(data=request.data, context={"tenant_id": request.user.tenant_id})
        serializer.is_valid(raise_exception=True)
        saved_data = serializer.save()
        return Response(saved_data)
