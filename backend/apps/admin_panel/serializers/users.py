from rest_framework import serializers
from rest_framework.fields import RegexValidator

from core.utils.serializers import ValidatorSerializer


class AdminTenantUsersFilterParams(ValidatorSerializer):
    SORT_FIELDS = (
        "first_name",
        "-first_name",
        "date_joined",
        "-date_joined",
    )

    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), default=[], required=False)
    search_field = serializers.ChoiceField(choices=("email", "first_name", "last_name"), required=False)
    search_value = serializers.CharField(required=False)


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
