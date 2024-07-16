from core.utils.serializers import ValidatorSerializer
from rest_framework import serializers


class ActivationLinkParams(ValidatorSerializer):
    send_activation_mail = serializers.BooleanField(required=False)


class ResetPasswordValidator(ValidatorSerializer):
    key = serializers.CharField(required=True)
    new_password = serializers.RegexField(
        regex=r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$",
        write_only=True,
        error_messages={
            "invalid": "Password must be at least 8 characters long with at least one capital letter and symbol"
        },
    )
    confirm_password = serializers.CharField(write_only=True, required=True)
