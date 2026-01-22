import logging

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView, Response

logger = logging.getLogger(__name__)


class MewsIntegrationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        """
        Handle Mews integration webhook.
        """
        logger.info("GET Received Mews integration webhook: %s", request.query_params)
        return Response({})

    def post(self, request, *args, **kwargs):
        """
        Handle Mews integration webhook.
        """
        logger.info("POST Received Mews integration webhook: %s", request.data)
        return Response({})
