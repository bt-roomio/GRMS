from typing import ClassVar, cast
from uuid import UUID

from django.db import models
from django.db.models import CASCADE
from django.utils import timezone

from core.models import BaseModel, BaseModelTs, UpdateByModel
from core.utils.files import controller_file
from core.utils.get_time import get_mil_sec
from core.utils.unix_timestamp import UnixTimeStampField
from services.models import BaseModel as ServiceBaseModel
from shuttle.querysets.attributes import AttributeKvQuerySet
from shuttle.querysets.controller import ControllerQuerySet
from shuttle.querysets.relation import RelationQuerySet
from shuttle.querysets.ts_kv import TsKvQuerySet
from shuttle.querysets.ts_kv_dictionary import TsKvDictionaryQuerySet
from shuttle.querysets.ts_kv_latest import TsKvLatestQuerySet


class TsKv(models.Model):
    ts: models.DateTimeField = models.DateTimeField(default=timezone.now, primary_key=True)
    entity = models.ForeignKey("main.Device", models.DO_NOTHING)
    entity_id = UUID
    key = models.ForeignKey("shuttle.TsKvDictionary", models.DO_NOTHING, to_field="key_id", db_column="key")
    bool_v = models.BooleanField(blank=True, null=True)
    str_v = models.TextField(blank=True, null=True)
    long_v = models.BigIntegerField(blank=True, null=True)
    dbl_v = models.FloatField(blank=True, null=True)
    json_v = models.JSONField(blank=True, null=True)

    objects = TsKvQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if self.ts is None:
            self.ts = get_mil_sec()
        super(TsKv, self).save(*args, **kwargs)

    class Meta(BaseModelTs.Meta):
        # Double check the migration for this model, it is not managed from django.
        managed = False
        db_table = "shuttle_ts_kv"
        unique_together = ("ts", "key", "entity")
        ordering = ("-ts",)


class TsKvDictionary(models.Model):
    key = models.CharField(max_length=255, unique=True)
    key_id = models.AutoField(unique=True, primary_key=True)

    objects: ClassVar[TsKvDictionaryQuerySet] = cast(TsKvDictionaryQuerySet, TsKvDictionaryQuerySet.as_manager())

    class Meta:
        db_table = "shuttle_ts_kv_dictionary"


class TsKvLatest(BaseModelTs):
    entity_id: UUID
    entity = models.ForeignKey("main.Device", models.DO_NOTHING, "ts_kvs_latest")
    key = models.ForeignKey("shuttle.TsKvDictionary", models.DO_NOTHING, to_field="key_id", db_column="key")
    bool_v = models.BooleanField(blank=True, null=True)
    str_v = models.TextField(blank=True, null=True)
    long_v = models.BigIntegerField(blank=True, null=True)
    dbl_v = models.FloatField(blank=True, null=True)
    json_v = models.JSONField(blank=True, null=True)

    objects: ClassVar[TsKvLatestQuerySet] = cast(TsKvLatestQuerySet, TsKvLatestQuerySet.as_manager())

    @property
    def get_value(self):
        """Get the first non-None value from value fields."""
        return next(
            (
                value
                for field in ("bool_v", "str_v", "dbl_v", "long_v", "json_v")
                if (value := getattr(self, field)) is not None
            ),
            None,
        )

    class Meta(BaseModelTs.Meta):
        db_table = "shuttle_ts_kv_latest"
        unique_together = ("entity", "key")


class AttributeKv(BaseModel):
    CLIENT_SCOPE = "CLIENT_SCOPE"
    SERVER_SCOPE = "SERVER_SCOPE"
    SHARED_SCOPE = "SHARED_SCOPE"
    ENTITY_TYPE = ((CLIENT_SCOPE, "CLIENT_SCOPE"), (SERVER_SCOPE, "SERVER_SCOPE"), (SHARED_SCOPE, "SHARED_SCOPE"))

    entity_type = models.CharField(max_length=255)
    entity = models.ForeignKey("main.Device", CASCADE, "attribute_kvs")
    entity_id: UUID
    attribute_type = models.CharField(max_length=255, choices=ENTITY_TYPE, default=SERVER_SCOPE)
    attribute_key = models.CharField(max_length=255)
    bool_v = models.BooleanField(blank=True, null=True)
    str_v = models.CharField(max_length=10000000, blank=True, null=True)
    long_v = models.BigIntegerField(blank=True, null=True)
    dbl_v = models.FloatField(blank=True, null=True)
    json_v = models.JSONField(blank=True, null=True)
    last_update_ts = UnixTimeStampField(default=get_mil_sec)

    objects: ClassVar[AttributeKvQuerySet] = cast(AttributeKvQuerySet, AttributeKvQuerySet.as_manager())

    @property
    def get_value(self):
        """Get the first non-None value from value fields."""
        return next(
            (
                value
                for field in ("bool_v", "str_v", "dbl_v", "long_v", "json_v")
                if (value := getattr(self, field)) is not None
            ),
            None,
        )

    def save(self, *args, **kwargs):
        if self.pk:
            self.last_update_ts = get_mil_sec()
        return super(AttributeKv, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.id)

    class Meta(BaseModel.Meta):
        db_table = "shuttle_attribute_kv"
        constraints = [
            models.UniqueConstraint(
                fields=["entity_type", "attribute_type", "entity_id", "attribute_key"],
                name="unique_attrkv_type_scope_entity_key",
            ),
        ]
        permissions = [
            ("view_attributelist", "Can view attribute lists"),
            ("add_attributelist", "Can add attribute lists"),
            ("add_attributerpc", "Can add attribute rpc"),
        ]


class Relation(BaseModel, UpdateByModel):
    from_id = models.ForeignKey("main.Device", CASCADE, "from_relations")
    from_type = models.CharField(max_length=255)
    to_id = models.ForeignKey("main.Device", CASCADE, "to_relations")
    to_type = models.CharField(max_length=255)
    relation_type_group = models.CharField(max_length=255)
    relation_type = models.CharField(max_length=255)
    additional_info = models.JSONField(blank=True, null=True)

    objects = RelationQuerySet.as_manager()

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table = "shuttle_relation"
        unique_together = (("from_id", "from_type", "relation_type_group", "relation_type", "to_id", "to_type"),)


class RPCMessage(models.Model):
    id: int
    created_at = models.DateTimeField(auto_now_add=True)
    received = models.BooleanField(default=False)
    additional_info = models.JSONField(blank=True, null=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        db_table = "shuttle_rpc_message"
        permissions = [
            ("send_jsonrpc", "Can send json rpc request"),
        ]


class ControllerFile(ServiceBaseModel):
    content = models.FileField(upload_to=controller_file)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    file_type = models.CharField(max_length=255, default="firmware")

    class Meta:
        db_table = "shuttle_controller_file"


class Controller(ServiceBaseModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    mac_address = models.CharField(max_length=255)
    file = models.ForeignKey(ControllerFile, CASCADE)
    tenant = models.ForeignKey("main.Tenant", CASCADE)

    objects = ControllerQuerySet.as_manager()

    class Meta:
        db_table = "shuttle_controller"
