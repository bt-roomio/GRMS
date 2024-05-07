from rest_framework.response import Response
from rest_framework.views import APIView

from main.serializers.change_email_config import ChangeEmailConfigSerializer


class ChangeEmailConfig(APIView):
    def put(self, request):
        serializer = ChangeEmailConfigSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
