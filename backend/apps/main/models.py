from django.db import models
from django.db.models import CASCADE, DO_NOTHING

from core.models import BaseModel


class Tenant(BaseModel):
    tenant_profile = models.ForeignKey('main.TenantProfile', DO_NOTHING)
    additional_info = models.CharField(blank=True, null=True)
    address = models.CharField(blank=True, null=True)
    address2 = models.CharField(blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    zip = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'main_tenant'


class TenantProfile(BaseModel):
    name = models.CharField(unique=True, max_length=255, blank=True, null=True)
    profile_data = models.JSONField(blank=True, null=True)
    description = models.CharField(blank=True, null=True)
    is_default = models.BooleanField(blank=True, null=True)
    isolated_tb_core = models.BooleanField(blank=True, null=True)
    isolated_tb_rule_engine = models.BooleanField(blank=True, null=True)

    class Meta:
        db_table = 'main_tenant_profile'


class AdminSettings(BaseModel):
    tenant = models.ForeignKey('main.Tenant', CASCADE)
    json_value = models.JSONField(blank=True, null=True)
    key = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'main_admin_settings'
