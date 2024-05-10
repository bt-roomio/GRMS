import time
import uuid

from django.db import models
from django.db.models import SET_NULL

from core.fields.unix_timestamp import UnixTimeStampField


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = UnixTimeStampField(default=time.time, editable=False, null=True)

    class Meta:
        abstract = True
        ordering = ('id',)


class UpdateByModel(models.Model):
    updated_at = UnixTimeStampField(default=time.time, null=True, )
    updated_by = models.ForeignKey('users.User', SET_NULL, null=True, blank=True,
                                   related_name='updated_%(model_name)ss')

    def save(self, **kwargs):
        if self.pk:
            self.updated_at = time.time()
        return super(UpdateByModel, self).save(**kwargs)

    class Meta:
        abstract = True
