from _typeshed import Incomplete
from django.db import models

from services.querysets.integration import IntegrationQuerySet

class BaseModel(models.Model):
    id: Incomplete
    created_at: Incomplete
    updated_at: Incomplete
    created_by: Incomplete
    updated_by: Incomplete

    class Meta:
        abstract: bool
        ordering: Incomplete

class Integration:
    TYPES: Incomplete
    name: Incomplete
    type: Incomplete
    description: Incomplete
    additional_info: Incomplete
    enable: Incomplete
    is_active: Incomplete
    tenant: Incomplete
    objects: IntegrationQuerySet

    class Meta:
        db_table: str
        constraints: Incomplete
