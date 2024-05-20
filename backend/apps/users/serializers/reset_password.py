from rest_framework import serializers
from core.utils.serializers import BaseSerializer, ValidatorSerializer


class GetResetLinkValidator(BaseSerializer):
    email = serializers.EmailField(required=True, write_only=True)


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
