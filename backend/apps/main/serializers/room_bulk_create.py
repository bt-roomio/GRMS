import re

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.fields import RegexValidator

from core.utils.serializers import ValidatorSerializer

ROOM_NUMBER_RE = r'^(?:\d+-\d+|\d+[A-Za-z]*)(?:;(?:\d+-\d+|\d+[A-Za-z]*))*;?$'

class RoomNumberValidator(ValidatorSerializer):
    number = serializers.CharField(
        required=True,
        validators=[
            RegexValidator(
                regex=ROOM_NUMBER_RE,
                flags=re.IGNORECASE,
                message=_("Invalid room number! Examples: '2', '2-3', '2-3;4;5', '2-3;4ab;5CD'"),
            )
        ],
    )
    floor = serializers.CharField(required=True)
    block = serializers.CharField(required=True)