from django.http import HttpResponse

from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from users.serializers.send_link import SendLinkParams
from users.utils.emails import send_reset_link_email
from users.views.jwt_token import AuthTokenThrottle

SendLinkSwagger = {"200": "Email sent", "400": "Invalid email format."}


class SendLinkView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthTokenThrottle]

    @swagger_auto_schema(tags=["Users, Send Link"], responses=SendLinkSwagger, request_body=SendLinkParams)
    def post(self, request):
        params = SendLinkParams(data=request.data)
        params.is_valid(raise_exception=True)

        # Answer identically whether or not the user was found: the 200/400 split
        # turned this endpoint into an account-existence oracle (unauthenticated
        # user enumeration).
        user = params.validated_data.get("user")  # pyright: ignore
        if user is not None:
            send_reset_link_email(user)

        return HttpResponse(b"Email sent")
