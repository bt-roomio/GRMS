from rest_framework import serializers
from rest_framework.fields import RegexValidator


class AdminChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        write_only=True,
        validators=[
            RegexValidator(
                regex=r"^(?=.*[A-Z])(?=.*\d).{9,}$",
                message="Password must be more than 8 characters, include at least one uppercase letter, and one number",
            )
        ],
    )
