import logging

from hoteza.serializers.checkout import CheckOutSerializer
from hoteza.utils.permissions import WhiteListPermission

from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class CheckOutListView(APIView):
    permission_classes = (WhiteListPermission,)

    def post(self, request):
        logger.info("Request data: %s", request.data)
        serializer = CheckOutSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.warning("Validation error: %s", e)
            logger.warning("Request data: %s", request.data)
            raise
        result = serializer.save()

        if isinstance(result, dict) and result.get("success") == False:
            return Response(result, status=400)

        return Response({"result": 0, "message": "Successfully checkout!"}, status=200)
