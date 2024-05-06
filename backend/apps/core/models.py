import time
import uuid

from django.db import models

from core.fields.unix_timestamp import UnixTimeStampField


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = UnixTimeStampField(default=time.time, editable=False, null=True)

    class Meta:
        abstract = True
        ordering = ('id',)
