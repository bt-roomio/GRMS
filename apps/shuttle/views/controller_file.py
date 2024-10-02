from rest_framework.response import Response
from rest_framework.views import APIView

from shuttle.serializers.controller_file import ControllerFileSerializer


class ControllerFileListView(APIView):
    def post(self, request):
        serializer = ControllerFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user, tenant_id=request.user.tenant_id)
        return Response(serializer.data)
