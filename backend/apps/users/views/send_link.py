from django.http import HttpResponse

from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from users.serializers.send_link import SendLinkParams
from users.utils.emails import send_reset_link_email

SendLinkSwagger = {"200": "Email sent", "400": "Email configuration is not configured or is incorrect."}


class SendLinkView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=["Users, Send Link"], responses=SendLinkSwagger, request_body=SendLinkParams)
    def post(self, request):
        params = SendLinkParams(data=request.data)
        params.is_valid(raise_exception=True)
        send_reset_link_email(params.validated_data["user"])  # pyright: ignore
        return HttpResponse(b"Email sent")
