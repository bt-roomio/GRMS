from typing import Any, Iterable, List
from uuid import UUID

from _typeshed import Incomplete
from django.db import models
from django.db.models.fields.related_managers import RelatedManager

from core.models import BaseModel, UpdateByModel
from main.querysets.dashboard import DashboardQuerySet
from main.querysets.device import DeviceQuerySet
from main.querysets.guest import GuestQuerySet
from main.querysets.public_space import PublicSpaceQuerySet
from main.querysets.room import RoomQuerySet
from main.querysets.room_type import RoomTypeQuerySet
from main.querysets.tenant import TenantQuerySet
from shuttle.models import Relation as Relation
from shuttle.models import TsKvDictionary as TsKvDictionary

class Tenant(BaseModel):
    tenant_profile: Incomplete
    additional_info: Incomplete
    address: Incomplete
    address2: Incomplete
    city: Incomplete
    country: Incomplete
    email: Incomplete
    phone: Incomplete
    region: Incomplete
    state: Incomplete
    title: Incomplete
    zip: Incomplete
    objects: TenantQuerySet

    class Meta(BaseModel.Meta):
        db_table: str
        permissions: Incomplete

class TenantProfile(BaseModel):
    name: Incomplete
    profile_data: Incomplete
    description: Incomplete
    is_default: Incomplete
    isolated_tb_core: Incomplete
    isolated_tb_rule_engine: Incomplete

    class Meta(BaseModel.Meta):
        db_table: str

class AdminSettings(BaseModel):
    tenant: Incomplete
    key: Incomplete
    json_value: Incomplete

    class Meta(BaseModel.Meta):
        db_table: str

class Room:
    Available: int
    CheckedIn: int
    Occupied: int
    Reserved: int
    MakeUpRoom: int

    AVAILABLE: str
    CHECKEDIN: str
    OCCUPIED: str
    RESERVED: str
    MAKEUPROOM: str

    STATE: Incomplete
    ON: str
    OFF: str
    STATUS: Incomplete

    id: UUID
    number: Incomplete
    floor: Incomplete
    block: Incomplete
    active: Incomplete
    state: list
    public_area_id: Incomplete
    pan_id: Incomplete
    building: Incomplete
    door_lock_device: Device
    type: Incomplete
    suite: Incomplete
    tenant: Tenant
    guests: RelatedManager[Guest]
    tenant_id: UUID
    status: Incomplete
    additional_info: Incomplete
    devices: List[Device]
    objects: RoomQuerySet

    def clean(self) -> None: ...
    def save(self, *args, **kwargs) -> None: ...
    def ts_kvs_latest_values(self, keys: Iterable[TsKvDictionary] | Iterable[str]) -> dict[str, Any]: ...

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table: str
        constraints: Incomplete
        permissions: Incomplete

class RoomHistory(BaseModel, UpdateByModel):
    number: Incomplete
    floor: Incomplete
    block: Incomplete
    active: Incomplete
    state: Incomplete
    public_area_id: Incomplete
    pan_id: Incomplete
    building: Incomplete
    door_lock_device: Device
    room_type: Incomplete
    suite: Incomplete
    tenant: Incomplete
    status: Incomplete
    room: Incomplete
    additional_info: Incomplete
    objects: Incomplete

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table: str
        default_related_name: str

class RoomType(BaseModel):
    title: Incomplete
    active: Incomplete
    check_in_out_address: Incomplete
    check_in_value: Incomplete
    check_out_value: Incomplete
    reserver_value: Incomplete
    app_server_sip_server_enable: Incomplete
    app_server_sip_account_num: Incomplete
    vip_status_address: Incomplete
    vip_status_on_value: Incomplete
    vip_status_off_value: Incomplete
    tenant: Incomplete
    tenant_id: Incomplete
    dashboard: Incomplete

    objects: RoomTypeQuerySet

    class Meta(BaseModel.Meta):
        db_table: str
        unique_together: Incomplete

class Device:
    id: UUID
    name: Incomplete
    type: Incomplete
    tenant: Incomplete
    tenant_id: UUID
    customer: Incomplete
    is_active: Incomplete
    device_profile_id: UUID
    device_profile: Incomplete
    status: Incomplete
    room: Incomplete
    label: Incomplete
    additional_info: Incomplete
    device_data: Incomplete
    external_id: Incomplete
    card: Incomplete
    relations: list[Relation]
    objects: DeviceQuerySet
    def clean(self) -> None: ...
    def save(self, *args, **kwargs) -> None: ...

    class Meta(BaseModel.Meta):
        db_table: str
        constraints: Incomplete
        permissions: Incomplete

class DeviceCredentials(BaseModel):
    credentials_id: Incomplete
    credentials_type: Incomplete
    credentials_value: Incomplete
    device: Incomplete
    objects: Incomplete

    class Meta(BaseModel.Meta):
        db_table: str

class DeviceProfile(BaseModel):
    name: Incomplete
    active: Incomplete
    tenant: Incomplete
    tenant_id: Incomplete
    type: Incomplete
    state: Incomplete
    image: Incomplete
    transport_type: Incomplete
    provision_type: Incomplete
    profile_data: Incomplete
    description: Incomplete
    is_default: Incomplete
    default_queue_name: Incomplete
    provision_device_key: Incomplete
    external_id: Incomplete
    objects: Incomplete
    def clean(self) -> None: ...
    def save(self, *args, **kwargs) -> None: ...

    class Meta(BaseModel.Meta):
        db_table: str
        constraints: Incomplete

class Customer(BaseModel):
    title: Incomplete
    tenant: Incomplete
    additional_info: Incomplete
    address: Incomplete
    address2: Incomplete
    city: Incomplete
    country: Incomplete
    email: Incomplete
    phone: Incomplete
    state: Incomplete
    zip: Incomplete
    external_id: Incomplete
    objects: Incomplete

    class Meta(BaseModel.Meta):
        db_table: str

class Dashboard(BaseModel):
    MAIN_DASHBOARD: str
    PUBLIC_SPACE_DASHBOARD: str
    title: Incomplete
    tenant: Incomplete
    tenant_id: Incomplete
    configuration: Incomplete
    assigned_customers: Incomplete
    mobile_hide: Incomplete
    mobile_order: Incomplete
    image: Incomplete
    external_id: Incomplete
    objects: DashboardQuerySet
    def clean(self) -> None: ...
    def save(self, *args, **kwargs) -> None: ...

    class Meta(BaseModel.Meta):
        db_table: str
        constraints: Incomplete
        permissions: Incomplete

class WidgetType(BaseModel):
    name: Incomplete
    tenant: Incomplete
    deprecated: Incomplete
    fqn: Incomplete
    descriptor: Incomplete
    image: Incomplete
    description: Incomplete
    tags: Incomplete
    external_id: Incomplete
    objects: Incomplete

    class Meta(BaseModel.Meta):
        db_table: str
        ordering: Incomplete
        unique_together: Incomplete

class Guest(BaseModel):
    class CHECKOUT_BY(models.TextChoices):
        ROOMIO = "roomio", "Roomio"
        PMS = "pms", "PMS"

    name: Incomplete
    lastname: Incomplete
    gender: Incomplete
    nationality: Incomplete
    language: Incomplete
    title: Incomplete
    is_active: Incomplete
    is_reservation: Incomplete
    pms_id: Incomplete
    birthday: Incomplete
    check_in: Incomplete
    check_out: Incomplete
    auto_check_out: Incomplete
    reservation_number: Incomplete
    room: Room
    room_id: UUID
    tenant: Incomplete
    tenant_id: Incomplete
    additional_info: Incomplete
    objects: GuestQuerySet
    checkout_by: CHECKOUT_BY
    def get_name(self): ...

    class Meta(BaseModel.Meta):
        db_table: str
        ordering: Incomplete
        permissions: Incomplete

class PublicSpace(BaseModel):
    floor: Incomplete
    block: Incomplete
    name: Incomplete
    accessible_for_guest: Incomplete
    tenant: Incomplete
    tenant_id: Incomplete
    dashboard: Incomplete
    additional_info: Incomplete
    objects: PublicSpaceQuerySet
    @property
    def devices(self): ...

    class Meta(BaseModel.Meta):
        db_table: str
        unique_together: Incomplete

class DevicePublicSpaces(BaseModel):
    device: Incomplete
    public_space: Incomplete
    objects: Incomplete
    def clean(self) -> None: ...

    class Meta(BaseModel.Meta):
        db_table: str
        unique_together: Incomplete
        default_related_name: str

class RoomTypePublicSpaces(BaseModel):
    room_type: Incomplete
    public_space: Incomplete
    objects: Incomplete

    class Meta(BaseModel.Meta):
        db_table: str
        unique_together: Incomplete
        default_related_name: str
