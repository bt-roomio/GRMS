import time
from datetime import datetime

from django.db import models
from rest_framework import serializers


class UnixTimeStampField(models.BigIntegerField):
    def get_prep_value(self, value):
        if isinstance(value, datetime):
            value = time.mktime(value.timetuple())
        return super().get_prep_value(value)

    def to_python(self, value):
        if isinstance(value, datetime):
            value = time.mktime(value.timetuple())
        return super().to_python(value)


class TimestampField(serializers.Field):
    def to_representation(self, value):
        """
        Convert a datetime object to a Unix timestamp (seconds since the epoch).
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            return int(time.mktime(value.timetuple()))
        raise serializers.ValidationError("This field requires a valid datetime object.")

    def to_internal_value(self, data):
        """
        Convert a Unix timestamp (integer) back to a datetime object.
        """
        if data is None:
            return None

        if isinstance(data, str) and data.isdigit():
            return int(data)
        raise serializers.ValidationError("This field requires an integer Unix timestamp.")
