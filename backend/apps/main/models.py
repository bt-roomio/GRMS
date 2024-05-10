from django.db import models
from django.db.models import CASCADE

from core.models import BaseModel, UpdateByModel


class Tenant(BaseModel):
    tenant_profile = models.ForeignKey('main.TenantProfile', CASCADE)
    additional_info = models.JSONField(default=dict)
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
    name = models.CharField(max_length=255, unique=True)
    profile_data = models.JSONField(default=dict)
    description = models.TextField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    isolated_tb_core = models.BooleanField(default=False)
    isolated_tb_rule_engine = models.BooleanField(default=False)

    class Meta:
        db_table = 'main_tenant_profile'


class AdminSettings(BaseModel):
    tenant = models.ForeignKey('main.Tenant', CASCADE)
    key = models.CharField(max_length=255)
    json_value = models.JSONField(default=dict)

    class Meta:
        db_table = 'main_admin_settings'


class EmailConfiguration(BaseModel, UpdateByModel):
    email = models.EmailField()
    host = models.CharField(max_length=255)
    port = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    use_tls = models.BooleanField(default=False)

    tenant = models.OneToOneField('main.Tenant', CASCADE)

    class Meta:
        db_table = 'main_email_configuration'
        default_related_name = 'email_configurations'
