import uuid

from django.db import models
from django.db.models import SET_NULL

from core.utils.get_time import get_mil_sec
from core.utils.unix_timestamp import UnixTimeStampField


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = UnixTimeStampField(default=get_mil_sec, editable=False, null=True)
    created_by = models.ForeignKey(
        "users.User", SET_NULL, null=True, blank=True, related_name="created_%(model_name)ss"
    )

    class Meta:
        abstract = True
        ordering = ("id",)


class NewUpdateByModel(models.Model):
    updated_at = models.DateTimeField(auto_now=True, editable=False, null=True)
    updated_by = models.ForeignKey("users.User", models.SET_NULL, "updated_%(model_name)ss", null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ("id",)


class BaseModelTs(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ts = UnixTimeStampField(default=get_mil_sec, null=True)

    class Meta:
        abstract = True
        ordering = ("id",)


class UpdateByModel(models.Model):
    updated_at = UnixTimeStampField(
        default=get_mil_sec,
        null=True,
    )
    updated_by = models.ForeignKey(
        "users.User",
        SET_NULL,
        null=True,
        blank=True,
        related_name="updated_%(model_name)ss",
    )

    def save(self, *args, **kwargs):
        if self.pk:
            self.updated_at = get_mil_sec()
        return super(UpdateByModel, self).save(*args, **kwargs)

    class Meta:
        abstract = True
