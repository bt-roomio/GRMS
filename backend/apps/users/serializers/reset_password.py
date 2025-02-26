from rest_framework import serializers
from rest_framework.fields import RegexValidator

from core.utils.serializers import ValidatorSerializer


class ActivationLinkParams(ValidatorSerializer):
    send_activation_mail = serializers.BooleanField(required=False)


class ResetPasswordValidator(ValidatorSerializer):
    key = serializers.CharField(required=True)
    new_password = serializers.CharField(
        write_only=True,
        validators=[
            RegexValidator(
                regex=r"^(?=.*[A-Z])(?=.*\d).{9,}$",
                message="Password must be more than 8 characters, include at least one uppercase letter, and one number",
            )
        ],
    )
    confirm_password = serializers.CharField(write_only=True, required=True)
