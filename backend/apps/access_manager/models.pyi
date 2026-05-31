from uuid import UUID

from _typeshed import Incomplete
from django.db import models

from access_manager.querysets.card import CardQuerySet
from access_manager.querysets.card_log import CardLogQuerySet
from access_manager.querysets.group import GroupQuerySet, GroupRoomQuerySet
from access_manager.querysets.guest_card import GuestCardQuerySet
from access_manager.querysets.need_sync import NeedSyncDeviceQuerySet
from access_manager.querysets.staff import StaffQuerySet
from core.models import BaseModel, UpdateByModel

class TypeChoices(models.IntegerChoices):
    HOUSEKEEPING: int
    ENGINEERING: int
    MASTER_CARD: int

class AccessGroupChoices(models.IntegerChoices):
    DENIED: int
    GUEST: int
    HOUSEKEEPING: int
    ENGINEERING: int
    MASTER_CARD: int
    FAILED: int
    SUCCESS = int

class Group(BaseModel, UpdateByModel):
    name: Incomplete
    tenant: Incomplete
    week_days: Incomplete
    start_time: Incomplete
    end_time: Incomplete
    expiry_date: Incomplete
    is_active: Incomplete
    additional_info: Incomplete
    group_type: Incomplete
    objects: GroupQuerySet

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table: str
        constraints: Incomplete

class Card(BaseModel, UpdateByModel):
    number: Incomplete
    tenant: Incomplete
    is_active: Incomplete
    KNX: Incomplete
    additional_info: Incomplete
    is_pwd: Incomplete
    objects: CardQuerySet

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table: str
        unique_together: Incomplete

class CardLog(BaseModel, UpdateByModel):
    created_at: Incomplete
    tenant: Incomplete
    number: Incomplete
    event_ts: Incomplete
    access_group: Incomplete
    device: Incomplete
    staff: Incomplete
    guest: Incomplete
    additional_info: Incomplete
    objects: CardLogQuerySet

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table: str
        ordering: Incomplete

class NeedSyncDevice(BaseModel, UpdateByModel):
    device: Incomplete
    card: Incomplete
    need_sync: Incomplete
    additional_info: Incomplete
    objects: NeedSyncDeviceQuerySet

    @property
    def get_card_holder_name(self): ...

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table: str

class Staff(BaseModel):
    first_name: Incomplete
    last_name: Incomplete
    is_active: Incomplete
    group: Incomplete
    group_id: UUID
    additional_info: Incomplete
    tenant: Incomplete
    objects: StaffQuerySet
    def get_name(self) -> str: ...

    class Meta(BaseModel.Meta):
        db_table: str
        constraints: Incomplete

class StaffCard(BaseModel):
    staff: Incomplete
    card: Incomplete
    is_active: Incomplete

    class Meta(BaseModel.Meta):
        db_table: str
        constraints: Incomplete

class GuestCard(BaseModel):
    guest: Incomplete
    card: Incomplete
    is_active: Incomplete
    is_blocked: Incomplete
    objects: GuestCardQuerySet

    class Meta(BaseModel.Meta):
        db_table: str
        constraints: Incomplete

class GroupRoom(BaseModel):
    group_id: UUID
    group: Incomplete
    room: Incomplete
    additional_info: Incomplete
    objects: GroupRoomQuerySet

    class Meta(BaseModel.Meta):
        db_table: str

class GroupPublicSpace(BaseModel):
    group_id: UUID
    group: Incomplete
    public_space: Incomplete
    additional_info: Incomplete

    class Meta(BaseModel.Meta):
        db_table: str

class GuestPublicSpace(BaseModel):
    guest: Incomplete
    public_space: Incomplete
    additional_info: Incomplete

    class Meta(BaseModel.Meta):
        db_table: str

class CardDeviceSlot(BaseModel, UpdateByModel):
    card_number: Incomplete
    device: Incomplete
    slot: Incomplete
    additional_info: Incomplete

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table: str
        unique_together: Incomplete
