from uuid import UUID

from _typeshed import Incomplete

from core.models import BaseModel, BaseModelTs, UpdateByModel
from shuttle.querysets.attributes import AttributeKvQuerySet
from shuttle.querysets.relation import RelationQuerySet
from shuttle.querysets.ts_kv import TsKvQuerySet
from shuttle.querysets.ts_kv_dictionary import TsKvDictionaryQuerySet
from shuttle.querysets.ts_kv_latest import TsKvLatestQuerySet

class TsKv:
    ts: Incomplete
    entity: Incomplete
    entity_id: UUID
    key: Incomplete
    bool_v: Incomplete
    str_v: Incomplete
    long_v: Incomplete
    dbl_v: Incomplete
    json_v: Incomplete
    objects: TsKvQuerySet
    def save(self, *args, **kwargs): ...

    class Meta:
        managed: bool
        db_table: str
        unique_together: Incomplete
        ordering: Incomplete

class TsKvDictionary:
    key: str
    key_id: int
    objects: TsKvDictionaryQuerySet

    class Meta:
        db_table: str

class TsKvLatest(BaseModelTs):
    entity_id: UUID
    entity: Incomplete
    key: Incomplete
    bool_v: Incomplete
    str_v: Incomplete
    long_v: Incomplete
    dbl_v: Incomplete
    json_v: Incomplete
    objects: TsKvLatestQuerySet

    @property
    def get_value(self): ...

    class Meta(BaseModelTs.Meta):
        db_table: str
        unique_together: Incomplete

class AttributeKv(BaseModel):
    CLIENT_SCOPE: str
    SERVER_SCOPE: str
    SHARED_SCOPE: str
    ENTITY_TYPE: tuple[tuple[str, str]]
    entity_type: Incomplete
    entity: Incomplete
    entity_id: UUID
    attribute_type: Incomplete
    attribute_key: Incomplete
    bool_v: Incomplete
    str_v: Incomplete
    long_v: Incomplete
    dbl_v: Incomplete
    json_v: Incomplete
    last_update_ts: Incomplete
    objects: AttributeKvQuerySet

    @property
    def get_value(self): ...
    def save(self, *args, **kwargs): ...

    class Meta(BaseModel.Meta):
        db_table: str
        constraints: Incomplete
        permissions: Incomplete

class Relation(BaseModel, UpdateByModel):
    from_id: Incomplete
    from_id_id: UUID
    from_type: Incomplete
    to_id: Incomplete
    to_id_id: UUID
    to_type: Incomplete
    relation_type_group: Incomplete
    relation_type: Incomplete
    additional_info: Incomplete
    objects: RelationQuerySet

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table: str
        unique_together: Incomplete

class RPCMessage:
    id: int
    created_at: Incomplete
    received: Incomplete
    additional_info: Incomplete

    class Meta:
        db_table: str
        permissions: Incomplete

class ControllerFile(BaseModel, UpdateByModel):
    content: Incomplete
    tenant: Incomplete
    file_type: Incomplete

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table: str

class Controller(BaseModel, UpdateByModel):
    name: Incomplete
    mac_address: Incomplete
    file: Incomplete
    tenant: Incomplete

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table: str
