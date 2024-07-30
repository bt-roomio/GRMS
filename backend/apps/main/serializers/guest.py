from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Guest


class GuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        fields = (
            "id",
            "name",
            "lastname",
            "gender",
            "nationality",
            "birthday",
            "is_active",
            "room",
            "check_in",
            "check_out",
            "auth_check_out",
            "reservation_number",
        )


class GuestFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
