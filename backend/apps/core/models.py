import time
import uuid

from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.BigIntegerField(default=time.time, editable=False, null=True)

    class Meta:
        abstract = True
        ordering = ('id',)
