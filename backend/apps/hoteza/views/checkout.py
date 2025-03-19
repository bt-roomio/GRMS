import logging

from hoteza.serializers.checkout import CheckOutSerializer
from hoteza.utils.permissions import WhiteListPermission

from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class CheckOutListView(APIView):
    permission_classes = (WhiteListPermission,)

    def post(self, request):
        serializer = CheckOutSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.error("Validation error: %s", e)
            logger.error("Request data: %s", request.data)
            raise
        serializer.save()
        return Response({"result": 0, "message": "Successfully checkout!"})
