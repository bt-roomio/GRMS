import time

from django.http import HttpResponse
from drf_yasg.utils import APIView, swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from users.models import ResetPassword, User
from users.serializers.reset_password import ActivationLinkParams, ResetPasswordValidator
from users.swagger.reset_password import ActivationLinkSwagger, ResetPasswordSwagger
from users.utils.emails import send_reset_link_email


class ActivationLinkView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(responses=ActivationLinkSwagger, query_serializer=ActivationLinkParams)
    def get(self, request, user_id):
        params = ActivationLinkParams.check(request.GET)
        user = get_object_or_404(User, pk=user_id)
        result = send_reset_link_email(user)
        if params.get("send_activation_mail"):
            return HttpResponse(b"Activation link sent.")
        return HttpResponse(result)


class ResetPasswordView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordValidator

    @swagger_auto_schema(responses=ResetPasswordSwagger)
    def put(self, request):
        data = self.serializer_class.check(request.data)
        reset = ResetPassword.objects.filter(key=data.get("key")).first()
        if not reset:
            raise ValidationError({"key": ["Invalid reset password token."]})

        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        if reset.expires_at < time.time():
            raise ValidationError({"key": ["Reset password token has expired."]})

        if new_password != confirm_password:
            raise ValidationError({"password": ["Passwords do not match."]})

        reset.user.set_password(new_password)
        reset.user.save()

        return Response({"message": "Password updated."})
