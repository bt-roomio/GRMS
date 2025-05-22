import logging

from hoteza.serializers.guest_change import GuestChangeSerializer
from hoteza.utils.permissions import WhiteListPermission

from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class GuestChangeListView(APIView):
    permission_classes = (WhiteListPermission,)

    def post(self, request):
        logger.debug("Request data: %s", request.data)
        serializer = GuestChangeSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.error("Validation error: %s", e)
            logger.error("Request data: %s", request.data)
            raise

        serializer.save()
        return Response({"result": 0, "message": "Successfully guestchanged!"})
