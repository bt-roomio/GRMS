from _typeshed import Incomplete
from django.db import models


class BaseModel(models.Model):
    id: Incomplete
    created_at: Incomplete
    created_by: Incomplete

    class Meta:
        abstract: bool
        ordering: Incomplete


class NewUpdateByModel(models.Model):
    updated_at: Incomplete
    updated_by: Incomplete

    class Meta:
        abstract: bool
        ordering: Incomplete


class BaseModelTs(models.Model):
    id: Incomplete
    ts: Incomplete

    class Meta:
        abstract: bool
        ordering: Incomplete


class UpdateByModel(models.Model):
    updated_at: Incomplete
    updated_by: Incomplete
    def save(self, *args, **kwargs): ...

    class Meta:
        abstract: bool
