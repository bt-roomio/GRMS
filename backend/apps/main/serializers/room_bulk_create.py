from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.fields import RegexValidator

from core.utils.serializers import ValidatorSerializer


class RoomNumberValidator(ValidatorSerializer):
    number = serializers.CharField(
        required=True,
        validators=[
            RegexValidator(
                regex=r"^(?:\d+(?:-\d+)?)(?:;\d+(?:-\d+)?)*;?$",
                message=_("Invalid room number! Exmples: '2', '2-3', '2-3;4;5'"),
            )
        ],
    )
