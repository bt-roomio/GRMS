import time
import uuid

from django.db import models
from django.db.models import CASCADE

from main.querysets.tenant import TenantQuerySet
from core.models import BaseModel, UpdateByModel
from main.querysets.room import RoomQuerySet


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

    STATUS = (
        (Available, "Available"),
        (CheckedIn, "CheckedIn"),
        (Occupied, "Occupied"),
        (DoNotDistrub, "DoNotDistrub"),
        (MakeUpRoom, "MakeUpRoom"),
    )

    room_number = models.IntegerField()
    floor = models.CharField(max_length=255)
    block = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    status = models.CharField(max_length=255, choices=STATUS, default=Available)
    public_area_id = models.IntegerField(null=True, blank=True)
    pan_id = models.CharField(max_length=255, null=True, blank=True)
    building = models.CharField(max_length=255, null=True, blank=True)
    door_lock_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    device = models.ForeignKey("main.Device", CASCADE, null=True, blank=True)
    type = models.ForeignKey("main.RoomType", CASCADE, null=True, blank=True)
    suite = models.ForeignKey("self", CASCADE, null=True, blank=True)
    tenant = models.ForeignKey("main.Tenant", CASCADE)

    objects = RoomQuerySet.as_manager()

    def __str__(self):
        return str(self.room_number)

    class Meta:
        db_table = "main_room"


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

    def __str__(self):
        return self.title

    class Meta:
        db_table = "main_room_type"


class Device(BaseModel):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", CASCADE)
    customer = models.ForeignKey("main.Customer", CASCADE)
    device_profile = models.ForeignKey("main.DeviceProfile", CASCADE)
    label = models.CharField(max_length=255, null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)
    device_data = models.JSONField(null=True, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    # firmware = models.ForeignKey("main.Firmware", CASCADE, null=True, blank=True)
    # software = models.ForeignKey("main.Software", CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "main_device"


class DeviceProfile(BaseModel):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
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
    # firmware = models.ForeignKey("OtaPackage", models.DO_NOTHING, blank=True, null=True)
    # software = models.ForeignKey(
    #     "OtaPackage", models.DO_NOTHING, related_name="deviceprofile_software_set", blank=True, null=True
    # )
    # default_rule_chain = models.ForeignKey("RuleChain", models.DO_NOTHING, blank=True, null=True)
    # default_dashboard = models.ForeignKey(Dashboard, models.DO_NOTHING, blank=True, null=True)
    # default_edge_rule_chain = models.ForeignKey(
    #     "RuleChain", models.DO_NOTHING, related_name="deviceprofile_default_edge_rule_chain_set", blank=True, null=True
    # )

    def __str__(self):
        return self.name

    class Meta:
        db_table = "main_device_profile"


class AttributeKv(BaseModel):
    CLIENT_SCOPE = "CLIENT_SCOPE"
    SERVER_SCOPE = "SERVER_SCOPE"
    SHARED_SCOPE = "SHARED_SCOPE"
    ENTITY_TYPE = ((CLIENT_SCOPE, "CLIENT_SCOPE"), (SERVER_SCOPE, "SERVER_SCOPE"), (SHARED_SCOPE, "SHARED_SCOPE"))

    entity_type = models.CharField(max_length=255)
    entity = models.ForeignKey("main.Device", CASCADE)
    attribute_type = models.CharField(max_length=255, choices=ENTITY_TYPE, default=SERVER_SCOPE)
    attribute_key = models.CharField(max_length=255)
    bool_v = models.BooleanField(blank=True, null=True)
    str_v = models.CharField(max_length=255, blank=True, null=True)
    long_v = models.BigIntegerField(blank=True, null=True)
    dbl_v = models.FloatField(blank=True, null=True)
    json_v = models.TextField(blank=True, null=True)
    last_update_ts = models.BigIntegerField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.pk:
            self.last_update_ts = time.time()
        return super(AttributeKv, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.entity)

    class Meta:
        db_table = "main_attribute_kv"


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
