import time

from django.db import transaction
from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView, GenericAPIView, get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from users.models import User, ResetPassword
from users.serializers.reset_password import GetResetLinkValidator, ResetPasswordValidator
from users.utils.emails import send_reset_link_email


class GetResetLinkView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = GetResetLinkValidator

    @transaction.atomic
    def perform_create(self, serializer):
        email = serializer.validated_data.get('email').lower()
        user = User.objects.filter(email=email).first()

        if not user:
            raise ValidationError({'email': ['There is not user with this email.']})

        result = send_reset_link_email(self.request, user)
        if result.get('success'):
            ResetPassword.objects.create(user=user)
        self.serializer_class.data = result


class ResetPasswordView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordValidator

    def put(self, request):
        data = self.serializer_class.check(request.data)
        reset = get_object_or_404(ResetPassword, key=data.get('key'))
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if reset.expires_at < time.time():
            raise ValidationError({'key': ['Reset password token has expired.']})

        if new_password != confirm_password:
            raise ValidationError({'password': ['Passwords do not match.']})

        reset.user.set_password(new_password)
        reset.user.save()

        return Response({'message': 'Password updated.'})
