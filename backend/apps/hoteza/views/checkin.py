import logging

from hoteza.serializers.checkin import CheckInSerializer

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class CheckInListView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        logger.debug(request.data)
        serializer = CheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"result": 0, "message": "Successfully checkin!"})
