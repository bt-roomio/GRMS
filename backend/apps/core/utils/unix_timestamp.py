import time
from datetime import datetime

from django.db import models


class UnixTimeStampField(models.BigIntegerField):
    def get_prep_value(self, value):
        if isinstance(value, datetime):
            value = time.mktime(value.timetuple())
        return super().get_prep_value(value)

    def to_python(self, value):
        if isinstance(value, datetime):
            value = time.mktime(value.timetuple())
        return super().to_python(value)
