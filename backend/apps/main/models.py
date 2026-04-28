from typing import Any, Dict, Iterable, Union
from uuid import UUID

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import CASCADE, SET_NULL, Manager, Q, UniqueConstraint
from django.db.models.functions import Lower

from rest_framework.exceptions import ValidationError

from core.models import BaseModel, UpdateByModel
from core.utils.unix_timestamp import UnixTimeStampField
from main.querysets.customer import CustomerQuerySet
from main.querysets.dashboard import DashboardQuerySet
from main.querysets.device import DeviceQuerySet
from main.querysets.device_credentials import DeviceCredentialsQuerySet
from main.querysets.device_profile import DeviceProfileQuerySet
from main.querysets.guest import GuestQuerySet
from main.querysets.public_space import DevicePublicSpacesQuerySet, PublicSpaceQuerySet, RoomTypePublicSpacesQuerySet
from main.querysets.room import RoomQuerySet
from main.querysets.room_history import RoomHistoryQuerySet
from main.querysets.room_type import RoomTypeQuerySet
from main.querysets.tenant import TenantQuerySet
from main.querysets.widget_type import WidgetTypeQuerySet
from main.utils.default_state import default_state
from services.models import BaseModel as ServiceBaseModel
from shuttle.models import Relation, TsKvDictionary, TsKvLatest


class Tenant(ServiceBaseModel):
    title = models.CharField(max_length=255, null=True, blank=True)
    tenant_profile = models.ForeignKey("main.TenantProfile", CASCADE)
    phone = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    address = models.CharField(null=True, blank=True)
    address2 = models.CharField(null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    zip = models.CharField(max_length=255, null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)

    objects = TenantQuerySet.as_manager()

    def __str__(self) -> str:
        return self.title

    objects = TenantQuerySet.as_manager()

    class Meta(ServiceBaseModel.Meta):
        db_table = "main_tenant"
        permissions = [
            ("view_alarmsettings", "Can view alarms"),
            ("change_alarmsettings", "Can change alarms"),
            ("view_generalsettings", "Can view general settings"),
            ("change_generalsettings", "Can change general settings"),
            ("view_integrationsettings", "Can view integration settings"),
            ("change_integrationsettings", "Can change integration settings"),
        ]


class TenantProfile(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    profile_data = models.JSONField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    isolated_tb_core = models.BooleanField(default=False)
    isolated_tb_rule_engine = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        db_table = "main_tenant_profile"


class AdminSettings(ServiceBaseModel):
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    key = models.CharField(max_length=255)
    json_value = models.JSONField(null=True, blank=True)

    class Meta(ServiceBaseModel.Meta):
        db_table = "main_admin_settings"


class Room(BaseModel, UpdateByModel):
    """
    If change Room model, don't forget about RoomHistory model.
    """

    Available = 0
    CheckedIn = 1
    Occupied = 2
    DoNotDisturb = 3
    MakeUpRoom = 4
    Reserved = 5

    AVAILABLE = "Available"
    CHECKEDIN = "CheckedIn"
    OCCUPIED = "Occupied"
    DONOTDISTURB = "DoNotDisturb"
    MAKEUPROOM = "MakeUpRoom"
    RESERVED = "Reserved"

    STATE = (
        (Available, AVAILABLE),
        (CheckedIn, CHECKEDIN),
        (Occupied, OCCUPIED),
        (DoNotDisturb, DONOTDISTURB),
        (MakeUpRoom, MAKEUPROOM),
        (Reserved, RESERVED),
    )

    ON = "ON"
    OFF = "OFF"
    STATUS = ((ON, "on"), (OFF, "off"))

    number = models.CharField(max_length=100)
    label = models.CharField(max_length=255, null=True, blank=True)
    floor = models.CharField(max_length=255)
    block = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    state = ArrayField(models.PositiveSmallIntegerField(choices=STATE), default=default_state)
    public_area_id = models.IntegerField(null=True, blank=True)
    pan_id = models.CharField(max_length=255, null=True, blank=True)
    building = models.CharField(max_length=255, null=True, blank=True)
    door_lock_device = models.OneToOneField(
        "main.Device", SET_NULL, null=True, blank=True, related_name="as_door_lock_room"
    )
    type = models.ForeignKey("main.RoomType", CASCADE, null=True, blank=True)
    suite = models.ForeignKey("self", CASCADE, null=True, blank=True)
    tenant = models.ForeignKey("main.Tenant", CASCADE, "rooms")
    status = models.CharField(max_length=255, choices=STATUS, default=OFF)
    additional_info = models.JSONField(null=True, blank=True)

    objects = RoomQuerySet.as_manager()

    def __str__(self):
        return self.number

    def clean(self):
        super().clean()
        if self.state is not None:
            if self.Available in self.state and self.CheckedIn in self.state:
                raise ValidationError(
                    {"state": "Поле state не может содержать одновременно состояния Available и CheckedIn."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        old_room_history_query = RoomHistory.objects.filter(room_id=self.pk)
        old_room_history = old_room_history_query and old_room_history_query.latest("created_at")

        if old_room_history:
            fields_to_check = ["number", "floor", "block", "active", "state", "status"]
            has_changed = any(getattr(old_room_history, field) != getattr(self, field) for field in fields_to_check)
            if has_changed:
                RoomHistory.objects.create(
                    number=self.number,
                    floor=self.floor,
                    block=self.block,
                    active=self.active,
                    state=self.state,
                    status=self.status,
                    tenant=self.tenant,
                    public_area_id=self.public_area_id,
                    pan_id=self.pan_id,
                    building=self.building,
                    door_lock_device=self.door_lock_device,
                    room_type=self.type,
                    suite=self.suite,
                    updated_at=self.updated_at,
                    updated_by=self.updated_by,
                    room_id=str(self.pk),
                )
        else:
            RoomHistory.objects.create(
                number=self.number,
                floor=self.floor,
                block=self.block,
                active=self.active,
                state=self.state,
                status=self.status,
                tenant=self.tenant,
                public_area_id=self.public_area_id,
                pan_id=self.pan_id,
                building=self.building,
                door_lock_device=self.door_lock_device,
                room_type=self.type,
                suite=self.suite,
                updated_at=self.updated_at,
                updated_by=self.updated_by,
                room_id=str(self.pk),
            )

    def ts_kvs_latest_values(self, keys: Union[Iterable[TsKvDictionary], Iterable[str]]) -> Dict[str, Any]:
        """
        Возвращает словарь {key_name: value} для всех ключей из списка keys.
        keys может быть списком объектов TsKvDictionary или списка строк-имен ключей.
        """
        # если передали строки, отфильтруем по названиям
        filter_kwargs = {}
        if keys and isinstance(next(iter(keys)), str):
            filter_kwargs["key__key__in"] = keys  # ключ.key – это строковое имя
        else:
            filter_kwargs["key__in"] = keys  # ключ – полноценный объект

        qs = (
            TsKvLatest.objects.filter(entity__room=self, **filter_kwargs)
            .select_related("key")
            .values_list("key__key", "long_v", "dbl_v")
        )
        result: Dict[str, Any] = {}
        for key_name, long_v, dbl_v in qs:
            # приоритет – long_v, если его нет, то dbl_v
            result[key_name] = long_v if long_v is not None else dbl_v
        return result

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table = "main_room"
        constraints = [
            UniqueConstraint(
                fields=["number", "floor", "block", "tenant"], condition=Q(active=True), name="unique_active_room"
            )
        ]
        permissions = [
            ("add_roomfromconf", "Can add room from conf"),
            ("view_roomstatus", "Can view room status"),
        ]


class RoomHistory(BaseModel, UpdateByModel):
    number = models.CharField(max_length=100)
    floor = models.CharField(max_length=255)
    block = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    state = ArrayField(models.PositiveSmallIntegerField(choices=Room.STATE), default=list)
    public_area_id = models.IntegerField(null=True, blank=True)
    pan_id = models.CharField(max_length=255, null=True, blank=True)
    building = models.CharField(max_length=255, null=True, blank=True)
    door_lock_device = models.OneToOneField(
        "main.Device", SET_NULL, null=True, blank=True, related_name="as_door_lock_device_history"
    )
    room_type = models.ForeignKey("main.RoomType", CASCADE, null=True, blank=True)
    suite = models.ForeignKey("self", CASCADE, null=True, blank=True)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    status = models.CharField(max_length=255, choices=Room.STATUS, default=Room.OFF)
    room = models.ForeignKey("main.Room", CASCADE)
    additional_info = models.JSONField(null=True, blank=True)

    objects = RoomHistoryQuerySet.as_manager()

    def __str__(self):
        return str(self.number)

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table = "main_room_history"
        default_related_name = "room_history"


class RoomType(BaseModel):
    title = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    check_in_out_address = models.IntegerField(null=True, blank=True)
    check_in_value = models.IntegerField(null=True, blank=True)
    check_out_value = models.IntegerField(null=True, blank=True)
    reserver_value = models.IntegerField(null=True, blank=True)
    app_server_sip_server_enable = models.BooleanField(null=True, blank=True)
    app_server_sip_account_num = models.IntegerField(null=True, blank=True)
    vip_status_address = models.IntegerField(null=True, blank=True)
    vip_status_on_value = models.IntegerField(null=True, blank=True)
    vip_status_off_value = models.IntegerField(null=True, blank=True)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    dashboard = models.ForeignKey("main.Dashboard", CASCADE, "room_types", null=True, blank=True)
    engineering_dashboard = models.ForeignKey(
        "main.Dashboard", CASCADE, "engineering_room_types", null=True, blank=True
    )

    objects = RoomTypeQuerySet.as_manager()

    def __str__(self):
        return str(self.title)

    class Meta(BaseModel.Meta):
        db_table = "main_room_type"
        unique_together = (("title", "tenant"),)


class Device(BaseModel):
    id: UUID
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    tenant_id: UUID
    customer = models.ForeignKey("main.Customer", CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    device_profile_id: UUID
    device_profile = models.ForeignKey("main.DeviceProfile", CASCADE, "devices")
    status = models.BooleanField(default=False)
    room = models.ForeignKey("main.Room", SET_NULL, "devices", null=True, blank=True)
    label = models.CharField(max_length=255, null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)
    device_data = models.JSONField(null=True, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    card = models.ForeignKey("access_manager.Card", SET_NULL, null=True, blank=True)

    relations: Manager["Relation"]

    objects = DeviceQuerySet.as_manager()

    def __str__(self):
        return str(self.name)

    def __repr__(self) -> str:
        return str(self.id)

    def clean(self):
        super().clean()
        if self.is_active:
            qs = Device.objects.filter(
                tenant=self.tenant,
                is_active=True,
                name__iexact=self.name,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({"name": "A device with this name, tenant, and active status already exists."})

        if self.room and self.device_public_spaces.exists():  # ty: ignore
            raise ValidationError({"room": "Device cannot be connected to a room and a public space at the same time."})

    def save(self, *args, **kwargs):
        self.full_clean()  # This will raise ValidationError if clean() fails.
        super().save(*args, **kwargs)

    class Meta(BaseModel.Meta):
        db_table = "main_device"
        constraints = [
            UniqueConstraint(
                Lower("name"), "tenant", condition=Q(is_active=True), name="unique_device_name_tenant_is_active"
            ),
        ]
        permissions = [
            ("add_devicefromconf", "Can add device from conf"),
        ]


class DeviceCredentials(BaseModel):
    credentials_id = models.CharField(unique=True, blank=True, null=True)
    credentials_type = models.CharField(max_length=255, blank=True, null=True)
    credentials_value = models.CharField(blank=True, null=True)
    device = models.OneToOneField("main.Device", CASCADE, blank=True, null=True, related_name="credentials")

    objects = DeviceCredentialsQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        db_table = "main_device_credentials"


class DeviceProfile(BaseModel):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    active = models.BooleanField(default=True)
    state = models.BooleanField(default=True)
    image = models.CharField(max_length=1000000, blank=True, null=True)
    transport_type = models.CharField(max_length=255, blank=True, null=True)
    provision_type = models.CharField(max_length=255, blank=True, null=True)
    profile_data = models.JSONField(blank=True, null=True)
    description = models.CharField(blank=True, null=True)
    is_default = models.BooleanField(blank=True, null=True)
    default_queue_name = models.CharField(max_length=255, blank=True, null=True)
    provision_device_key = models.CharField(unique=True, blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    objects = DeviceProfileQuerySet.as_manager()

    def clean(self):
        super().clean()
        if self.active:
            qs = DeviceProfile.objects.filter(
                tenant=self.tenant,
                active=True,
                name__iexact=self.name,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"name": "A device profile with this name, tenant, and active status already exists."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()  # This will raise ValidationError if clean() fails.
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name)

    class Meta(BaseModel.Meta):
        db_table = "main_device_profile"
        constraints = [
            UniqueConstraint(Lower("name"), "tenant", condition=Q(active=True), name="unique_active_device_profile")
        ]


class Customer(BaseModel):
    title = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    additional_info = models.JSONField(blank=True, null=True)
    address = models.CharField(blank=True, null=True)
    address2 = models.CharField(blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    zip = models.CharField(max_length=255, blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    objects = CustomerQuerySet.as_manager()

    def __str__(self):
        return str(self.title)

    class Meta(BaseModel.Meta):
        db_table = "main_customer"


class Dashboard(BaseModel):
    MAIN_DASHBOARD = "main_dashboard"
    PUBLIC_SPACE_DASHBOARD = "public_space_dashboard"

    title = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    configuration = models.JSONField(blank=True, null=True)
    assigned_customers = models.CharField(max_length=255, blank=True, null=True)
    mobile_hide = models.BooleanField(default=False)
    mobile_order = models.IntegerField(blank=True, null=True)
    image = models.ImageField(upload_to="dashboard", null=True, blank=True)
    external_id = models.UUIDField(blank=True, null=True)

    objects = DashboardQuerySet.as_manager()

    def clean(self):
        super().clean()
        qs = Dashboard.objects.filter(
            tenant=self.tenant,
            title__iexact=self.title,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({"name": "A dashboard with this title and tenant already exists."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.title)

    class Meta(BaseModel.Meta):
        db_table = "main_dashboard"
        constraints = [UniqueConstraint(Lower("title"), "tenant", name="unique_dashboard_title_tenant")]
        permissions = [
            ("view_dashboardtype", "Can view dashboard types"),
        ]


class WidgetType(BaseModel):
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    deprecated = models.BooleanField(default=False)
    fqn = models.CharField(max_length=512, blank=True, null=True)
    descriptor = models.JSONField(blank=True, null=True)
    image = models.CharField(max_length=1000000, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    tags = models.TextField(blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    objects = WidgetTypeQuerySet.as_manager()

    def __str__(self):
        return str(self.name)

    class Meta(BaseModel.Meta):
        db_table = "main_widget_type"
        ordering = ["created_at"]
        unique_together = ("name", "tenant")


class Guest(BaseModel):
    class CHECKOUT_BY(models.TextChoices):
        ROOMIO = "roomio", "Roomio"
        PMS = "pms", "PMS"

    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_reservation = models.BooleanField(default=False)
    reservation_number = models.CharField(max_length=255, null=True, blank=True)
    lastname = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=255, null=True, blank=True)
    nationality = models.CharField(max_length=255, null=True, blank=True)  # Make standart nationality
    language = models.CharField(max_length=255, null=True, blank=True)  # Make standart language
    title = models.CharField(max_length=255, null=True, blank=True)
    birthday = UnixTimeStampField(null=True, blank=True)
    check_in = UnixTimeStampField(null=True, blank=True)
    check_out = UnixTimeStampField(null=True, blank=True)
    auto_check_out = models.BooleanField(default=False)
    room = models.ForeignKey("main.Room", SET_NULL, "guests", null=True, blank=True)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    pms_id = models.CharField(max_length=255, null=True, blank=True)
    additional_info = models.JSONField(blank=True, null=True)
    checkout_by = models.CharField(choices=CHECKOUT_BY.choices, max_length=50, null=True, blank=True)

    objects = GuestQuerySet.as_manager()

    def __str__(self):
        return str(f"{self.name} {self.lastname} in {self.room}")

    def get_name(self):
        return str(self.name + " " + self.lastname)

    class Meta(BaseModel.Meta):
        db_table = "main_guest"
        ordering = ["created_at"]
        permissions = [
            ("change_guestmoveroom", "Can change guest move room"),
        ]


class PublicSpace(BaseModel):
    floor = models.CharField(max_length=255)
    block = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    accessible_for_guest = models.BooleanField(default=False)
    tenant = models.ForeignKey("main.Tenant", models.CASCADE)
    dashboard = models.ForeignKey("main.Dashboard", models.SET_NULL, null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)

    objects = PublicSpaceQuerySet.as_manager()

    def __str__(self):
        return str(self.name)

    @property
    def devices(self):
        return Device.objects.filter(device_public_spaces__public_space=self)

    class Meta(BaseModel.Meta):
        db_table = "main_public_spaces"
        unique_together = ("name", "tenant")


class DevicePublicSpaces(BaseModel):
    device = models.ForeignKey("main.Device", CASCADE)
    public_space = models.ForeignKey("main.PublicSpace", CASCADE)

    objects = DevicePublicSpacesQuerySet.as_manager()

    def clean(self):
        super().clean()
        if self.device.tenant != self.public_space.tenant:
            raise ValidationError({"tenant": "Device's tenant and Public Space's tenant must be the same."})
        if self.device.room:
            raise ValidationError(
                {"device": "Device is already connected to a room and cannot be linked to a public space."}
            )

    class Meta(BaseModel.Meta):
        db_table = "main_device_public_spaces"
        unique_together = ("device", "public_space")
        default_related_name = "device_public_spaces"


class RoomTypePublicSpaces(BaseModel):
    room_type = models.ForeignKey("main.RoomType", CASCADE)
    public_space = models.ForeignKey("main.PublicSpace", CASCADE)

    objects = RoomTypePublicSpacesQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        db_table = "main_room_type_public_spaces"
        unique_together = ("room_type", "public_space")
        default_related_name = "room_type_public_spaces"
