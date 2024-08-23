from django.db import models
from django.db.models import CASCADE, SET_NULL

from core.models import BaseModel, UpdateByModel
from core.utils.unix_timestamp import UnixTimeStampField
from main.querysets.dashboard import DashboardQuerySet
from main.querysets.device import DeviceQuerySet
from main.querysets.device_credentials import DeviceCredentialsQuerySet
from main.querysets.device_profile import DeviceProfileQuerySet
from main.querysets.guest import GuestQuerySet
from main.querysets.room import RoomQuerySet
from main.querysets.room_type import RoomTypeQuerySet
from main.querysets.tenant import TenantQuerySet
from main.querysets.widget_type import WidgetTypeQuerySet


class Tenant(BaseModel):
    tenant_profile = models.ForeignKey("main.TenantProfile", CASCADE)
    additional_info = models.JSONField(null=True, blank=True)
    address = models.CharField(null=True, blank=True)
    address2 = models.CharField(null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    zip = models.CharField(max_length=255, null=True, blank=True)

    objects = TenantQuerySet.as_manager()

    class Meta:
        db_table = "main_tenant"


class TenantProfile(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    profile_data = models.JSONField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    isolated_tb_core = models.BooleanField(default=False)
    isolated_tb_rule_engine = models.BooleanField(default=False)

    class Meta:
        db_table = "main_tenant_profile"


class AdminSettings(BaseModel):
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    key = models.CharField(max_length=255)
    json_value = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "main_admin_settings"


class EmailConfiguration(BaseModel, UpdateByModel):
    email = models.EmailField()
    host = models.CharField(max_length=255)
    port = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    use_tls = models.BooleanField(default=True)
    frontend_host = models.CharField(max_length=255, null=True, blank=True)
    frontend_port = models.CharField(max_length=100, null=True, blank=True)

    tenant = models.OneToOneField("main.Tenant", CASCADE)

    class Meta:
        db_table = "main_email_configuration"
        default_related_name = "email_configurations"


class Room(BaseModel, UpdateByModel):
    Available = "Available"
    CheckedIn = "CheckedIn"
    Occupied = "Occupied"
    DoNotDistrub = "DoNotDistrub"
    MakeUpRoom = "MakeUpRoom"

    STATE = (
        (Available, "Available"),
        (CheckedIn, "CheckedIn"),
        (Occupied, "Occupied"),
        (DoNotDistrub, "DoNotDistrub"),
        (MakeUpRoom, "MakeUpRoom"),
    )

    ON = "ON"
    OFF = "OFF"
    STATUS = ((ON, "on"), (OFF, "off"))

    room_number = models.IntegerField()
    floor = models.CharField(max_length=255)
    block = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    state = models.CharField(max_length=255, choices=STATE, default=Available)
    public_area_id = models.IntegerField(null=True, blank=True)
    pan_id = models.CharField(max_length=255, null=True, blank=True)
    building = models.CharField(max_length=255, null=True, blank=True)
    door_lock_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    type = models.ForeignKey("main.RoomType", CASCADE, null=True, blank=True)
    suite = models.ForeignKey("self", CASCADE, null=True, blank=True)
    tenant = models.ForeignKey("main.Tenant", CASCADE)

    # Helpers
    status = models.CharField(max_length=255, choices=STATUS, default=OFF)

    objects = RoomQuerySet.as_manager()

    def __str__(self):
        return str(self.room_number)

    class Meta:
        db_table = "main_room"


class RoomType(BaseModel):
    title = models.CharField(max_length=255, unique=True)
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
    dashboard = models.ForeignKey("main.Dashboard", CASCADE, null=True, blank=True)

    objects = RoomTypeQuerySet.as_manager()

    def __str__(self):
        return str(self.title)

    class Meta:
        db_table = "main_room_type"


class Device(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    customer = models.ForeignKey("main.Customer", CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    device_profile = models.ForeignKey("main.DeviceProfile", CASCADE)
    status = models.BooleanField(default=False)
    room = models.ForeignKey("main.Room", SET_NULL, "devices", null=True, blank=True)
    label = models.CharField(max_length=255, null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)
    device_data = models.JSONField(null=True, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)

    objects = DeviceQuerySet.as_manager()

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "main_device"


class DeviceCredentials(BaseModel):
    credentials_id = models.CharField(unique=True, blank=True, null=True)
    credentials_type = models.CharField(max_length=255, blank=True, null=True)
    credentials_value = models.CharField(blank=True, null=True)
    device = models.OneToOneField("main.Device", CASCADE, blank=True, null=True, related_name="credentials")

    objects = DeviceCredentialsQuerySet.as_manager()

    class Meta:
        db_table = "main_device_credentials"


class DeviceProfile(BaseModel):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    state = models.BooleanField(default=True)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
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

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "main_device_profile"


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

    def __str__(self):
        return str(self.title)

    class Meta:
        db_table = "main_customer"


class Dashboard(BaseModel):
    title = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    configuration = models.JSONField(blank=True, null=True)
    assigned_customers = models.CharField(max_length=255, blank=True, null=True)
    mobile_hide = models.BooleanField(default=False)
    mobile_order = models.IntegerField(blank=True, null=True)
    image = models.ImageField(upload_to="dashboard", null=True, blank=True)
    external_id = models.UUIDField(blank=True, null=True)

    objects = DashboardQuerySet.as_manager()

    def __str__(self):
        return str(self.title)

    class Meta:
        db_table = "main_dashboard"


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

    class Meta:
        db_table = "main_widget_type"
        ordering = ["created_at"]
        unique_together = ("name", "tenant")


class Guest(BaseModel):
    name = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=255, null=True, blank=True)
    nationality = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    birthday = UnixTimeStampField(null=True, blank=True)
    check_in = UnixTimeStampField(null=True, blank=True)
    check_out = UnixTimeStampField(null=True, blank=True)
    auto_check_out = models.BooleanField(default=False)
    reservation_number = models.CharField(max_length=255, null=True, blank=True)
    room = models.ForeignKey("main.Room", SET_NULL, "guests", null=True, blank=True)
    tenant = models.ForeignKey("main.Tenant", CASCADE)

    objects = GuestQuerySet.as_manager()

    class Meta:
        db_table = "main_guest"
        ordering = ["created_at"]
