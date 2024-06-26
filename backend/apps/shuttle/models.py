import time
from django.db import models
from django.db.models import CASCADE

from core.models import BaseModel, BaseModelTs
from shuttle.querysets.ts_kv_dictionary import TsKvDictionaryQuerySet
from shuttle.querysets.ts_kv_latest import TsKvLatestQuerySet
from shuttle.querysets.ts_kv import TsKvQuerySet
from shuttle.querysets.attributes import AttributeKvQuerySet


class TsKv(BaseModelTs):
    entity = models.ForeignKey("main.Device", models.DO_NOTHING)
    key = models.IntegerField()
    bool_v = models.BooleanField(blank=True, null=True)
    str_v = models.CharField(max_length=255, blank=True, null=True)
    long_v = models.BigIntegerField(blank=True, null=True)
    dbl_v = models.FloatField(blank=True, null=True)
    json_v = models.JSONField(blank=True, null=True)

    objects = TsKvQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        db_table = "shuttle_ts_kv"
        unique_together = ("entity", "key", "ts")


class TsKvDictionary(models.Model):
    key = models.CharField(max_length=255)
    key_id = models.AutoField(unique=True, primary_key=True)

    objects = TsKvDictionaryQuerySet.as_manager()

    class Meta:
        db_table = "shuttle_ts_kv_dictionary"


class TsKvLatest(BaseModelTs):
    entity = models.ForeignKey("main.Device", models.DO_NOTHING)
    key = models.IntegerField()
    bool_v = models.BooleanField(blank=True, null=True)
    str_v = models.CharField(max_length=255, blank=True, null=True)
    long_v = models.BigIntegerField(blank=True, null=True)
    dbl_v = models.FloatField(blank=True, null=True)
    json_v = models.JSONField(blank=True, null=True)

    objects = TsKvLatestQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        db_table = "shuttle_ts_kv_latest"
        unique_together = ("entity", "key")


class AttributeKv(BaseModel):
    CLIENT_SCOPE = "CLIENT_SCOPE"
    SERVER_SCOPE = "SERVER_SCOPE"
    SHARED_SCOPE = "SHARED_SCOPE"
    ENTITY_TYPE = ((CLIENT_SCOPE, "CLIENT_SCOPE"), (SERVER_SCOPE, "SERVER_SCOPE"), (SHARED_SCOPE, "SHARED_SCOPE"))

    entity_type = models.CharField(max_length=255)
    entity = models.ForeignKey("main.Device", CASCADE, "attribute_kvs")
    attribute_type = models.CharField(max_length=255, choices=ENTITY_TYPE, default=SERVER_SCOPE)
    attribute_key = models.CharField(max_length=255)
    bool_v = models.BooleanField(blank=True, null=True)
    str_v = models.CharField(max_length=255, blank=True, null=True)
    long_v = models.BigIntegerField(blank=True, null=True)
    dbl_v = models.FloatField(blank=True, null=True)
    json_v = models.TextField(blank=True, null=True)
    last_update_ts = models.BigIntegerField(blank=True, null=True)

    objects = AttributeKvQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if self.pk:
            self.last_update_ts = time.time()
        return super(AttributeKv, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.entity)

    class Meta:
        db_table = "shuttle_attribute_kv"
