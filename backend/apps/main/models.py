import uuid

from django.db import models
from django.db.models import CASCADE

from main.querysets.tenant import TenantQuerySet
from core.models import BaseModel, UpdateByModel
from main.querysets.room import RoomQuerySet


class Tenant(BaseModel):
    tenant_profile = models.ForeignKey('main.TenantProfile', CASCADE)
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
        db_table = 'main_tenant'


class TenantProfile(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    profile_data = models.JSONField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    isolated_tb_core = models.BooleanField(default=False)
    isolated_tb_rule_engine = models.BooleanField(default=False)

    class Meta:
        db_table = 'main_tenant_profile'


class AdminSettings(BaseModel):
    tenant = models.ForeignKey('main.Tenant', CASCADE)
    key = models.CharField(max_length=255)
    json_value = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'main_admin_settings'


class EmailConfiguration(BaseModel, UpdateByModel):
    email = models.EmailField()
    host = models.CharField(max_length=255)
    port = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    use_tls = models.BooleanField(default=True)

    tenant = models.OneToOneField('main.Tenant', CASCADE)

    class Meta:
        db_table = 'main_email_configuration'
        default_related_name = 'email_configurations'


class Room(BaseModel, UpdateByModel):
    Available = 'Available'
    CheckedIn = 'CheckedIn'
    Occupied = 'Occupied'
    DoNotDistrub = 'DoNotDistrub'
    MakeUpRoom = 'MakeUpRoom'

    STATUS = (
        (Available, 'Available'),
        (CheckedIn, 'CheckedIn'),
        (Occupied, 'Occupied'),
        (DoNotDistrub, 'DoNotDistrub'),
        (MakeUpRoom, 'MakeUpRoom'),
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
    device = models.ForeignKey('main.Device', CASCADE, null=True, blank=True)
    type = models.ForeignKey('main.RoomType', CASCADE, null=True, blank=True)
    suite = models.ForeignKey('self', CASCADE, null=True, blank=True)
    tenant = models.ForeignKey('main.Tenant', CASCADE)

    objects = RoomQuerySet.as_manager()

    def __str__(self):
        return str(self.room_number)

    class Meta:
        db_table = 'main_room'


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
    tenant = models.ForeignKey('main.Tenant', CASCADE)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'main_room_type'

class Device(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'main_device'
