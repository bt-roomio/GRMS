# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AdminSettings(models.Model):
    id = models.UUIDField(primary_key=True)
    tenant_id = models.UUIDField()
    created_time = models.BigIntegerField()
    json_value = models.CharField(blank=True, null=True)
    key = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'admin_settings'


class Alarm(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    ack_ts = models.BigIntegerField(blank=True, null=True)
    clear_ts = models.BigIntegerField(blank=True, null=True)
    additional_info = models.CharField(blank=True, null=True)
    end_ts = models.BigIntegerField(blank=True, null=True)
    originator_id = models.UUIDField(blank=True, null=True)
    originator_type = models.IntegerField(blank=True, null=True)
    propagate = models.BooleanField(blank=True, null=True)
    severity = models.CharField(max_length=255, blank=True, null=True)
    start_ts = models.BigIntegerField(blank=True, null=True)
    assign_ts = models.BigIntegerField(blank=True, null=True)
    assignee_id = models.UUIDField(blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    customer_id = models.UUIDField(blank=True, null=True)
    propagate_relation_types = models.CharField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    propagate_to_owner = models.BooleanField(blank=True, null=True)
    propagate_to_tenant = models.BooleanField(blank=True, null=True)
    acknowledged = models.BooleanField(blank=True, null=True)
    cleared = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'alarm'


class AlarmComment(models.Model):
    id = models.UUIDField()
    created_time = models.BigIntegerField()
    alarm = models.ForeignKey(Alarm, models.DO_NOTHING)
    user_id = models.UUIDField(blank=True, null=True)
    type = models.CharField(max_length=255)
    comment = models.CharField(max_length=10000, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'alarm_comment'


class AlarmTypes(models.Model):
    tenant = models.ForeignKey('Tenant', models.DO_NOTHING)
    type = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'alarm_types'
        unique_together = (('tenant', 'type'),)


class ApiUsageState(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    tenant_id = models.UUIDField(blank=True, null=True)
    entity_type = models.CharField(max_length=32, blank=True, null=True)
    entity_id = models.UUIDField(blank=True, null=True)
    transport = models.CharField(max_length=32, blank=True, null=True)
    db_storage = models.CharField(max_length=32, blank=True, null=True)
    re_exec = models.CharField(max_length=32, blank=True, null=True)
    js_exec = models.CharField(max_length=32, blank=True, null=True)
    tbel_exec = models.CharField(max_length=32, blank=True, null=True)
    email_exec = models.CharField(max_length=32, blank=True, null=True)
    sms_exec = models.CharField(max_length=32, blank=True, null=True)
    alarm_exec = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'api_usage_state'
        unique_together = (('tenant_id', 'entity_id'),)


class Asset(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    additional_info = models.CharField(blank=True, null=True)
    customer_id = models.UUIDField(blank=True, null=True)
    asset_profile = models.ForeignKey('AssetProfile', models.DO_NOTHING)
    name = models.CharField(max_length=255, blank=True, null=True)
    label = models.CharField(max_length=255, blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'asset'
        unique_together = (('tenant_id', 'external_id'), ('tenant_id', 'name'),)


class AssetProfile(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    name = models.CharField(max_length=255, blank=True, null=True)
    image = models.CharField(max_length=1000000, blank=True, null=True)
    description = models.CharField(blank=True, null=True)
    is_default = models.BooleanField(blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    default_rule_chain = models.ForeignKey('RuleChain', models.DO_NOTHING, blank=True, null=True)
    default_dashboard = models.ForeignKey('Dashboard', models.DO_NOTHING, blank=True, null=True)
    default_queue_name = models.CharField(max_length=255, blank=True, null=True)
    default_edge_rule_chain = models.ForeignKey('RuleChain', models.DO_NOTHING, related_name='assetprofile_default_edge_rule_chain_set', blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'asset_profile'
        unique_together = (('tenant_id', 'external_id'), ('tenant_id', 'name'),)


class AttributeKv(models.Model):
    entity_type = models.CharField(primary_key=True, max_length=255)  # The composite primary key (entity_type, entity_id, attribute_type, attribute_key) found, that is not supported. The first column is selected.
    entity_id = models.UUIDField()
    attribute_type = models.CharField(max_length=255)
    attribute_key = models.CharField(max_length=255)
    bool_v = models.BooleanField(blank=True, null=True)
    str_v = models.CharField(max_length=10000000, blank=True, null=True)
    long_v = models.BigIntegerField(blank=True, null=True)
    dbl_v = models.FloatField(blank=True, null=True)
    json_v = models.TextField(blank=True, null=True)  # This field type is a guess.
    last_update_ts = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'attribute_kv'
        unique_together = (('entity_type', 'entity_id', 'attribute_type', 'attribute_key'),)


class AuditLog(models.Model):
    id = models.UUIDField()
    created_time = models.BigIntegerField()
    tenant_id = models.UUIDField(blank=True, null=True)
    customer_id = models.UUIDField(blank=True, null=True)
    entity_id = models.UUIDField(blank=True, null=True)
    entity_type = models.CharField(max_length=255, blank=True, null=True)
    entity_name = models.CharField(max_length=255, blank=True, null=True)
    user_id = models.UUIDField(blank=True, null=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    action_type = models.CharField(max_length=255, blank=True, null=True)
    action_data = models.CharField(max_length=1000000, blank=True, null=True)
    action_status = models.CharField(max_length=255, blank=True, null=True)
    action_failure_details = models.CharField(max_length=1000000, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'audit_log'


class ComponentDescriptor(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    actions = models.CharField(max_length=255, blank=True, null=True)
    clazz = models.CharField(unique=True, blank=True, null=True)
    configuration_descriptor = models.CharField(blank=True, null=True)
    configuration_version = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    scope = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    clustering_mode = models.CharField(max_length=255, blank=True, null=True)
    has_queue_name = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'component_descriptor'


class Customer(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    additional_info = models.CharField(blank=True, null=True)
    address = models.CharField(blank=True, null=True)
    address2 = models.CharField(blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    zip = models.CharField(max_length=255, blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'customer'
        unique_together = (('tenant_id', 'external_id'),)


class Dashboard(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    configuration = models.CharField(blank=True, null=True)
    assigned_customers = models.CharField(max_length=1000000, blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    mobile_hide = models.BooleanField(blank=True, null=True)
    mobile_order = models.IntegerField(blank=True, null=True)
    image = models.CharField(max_length=1000000, blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dashboard'
        unique_together = (('tenant_id', 'external_id'),)


class Device(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    additional_info = models.CharField(blank=True, null=True)
    customer_id = models.UUIDField(blank=True, null=True)
    device_profile = models.ForeignKey('DeviceProfile', models.DO_NOTHING)
    device_data = models.JSONField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    label = models.CharField(max_length=255, blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    firmware = models.ForeignKey('OtaPackage', models.DO_NOTHING, blank=True, null=True)
    software = models.ForeignKey('OtaPackage', models.DO_NOTHING, related_name='device_software_set', blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'device'
        unique_together = (('tenant_id', 'external_id'), ('tenant_id', 'name'),)


class DeviceCredentials(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    credentials_id = models.CharField(unique=True, blank=True, null=True)
    credentials_type = models.CharField(max_length=255, blank=True, null=True)
    credentials_value = models.CharField(blank=True, null=True)
    device_id = models.UUIDField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'device_credentials'


class DeviceProfile(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    name = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    image = models.CharField(max_length=1000000, blank=True, null=True)
    transport_type = models.CharField(max_length=255, blank=True, null=True)
    provision_type = models.CharField(max_length=255, blank=True, null=True)
    profile_data = models.JSONField(blank=True, null=True)
    description = models.CharField(blank=True, null=True)
    is_default = models.BooleanField(blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    firmware = models.ForeignKey('OtaPackage', models.DO_NOTHING, blank=True, null=True)
    software = models.ForeignKey('OtaPackage', models.DO_NOTHING, related_name='deviceprofile_software_set', blank=True, null=True)
    default_rule_chain = models.ForeignKey('RuleChain', models.DO_NOTHING, blank=True, null=True)
    default_dashboard = models.ForeignKey(Dashboard, models.DO_NOTHING, blank=True, null=True)
    default_queue_name = models.CharField(max_length=255, blank=True, null=True)
    provision_device_key = models.CharField(unique=True, blank=True, null=True)
    default_edge_rule_chain = models.ForeignKey('RuleChain', models.DO_NOTHING, related_name='deviceprofile_default_edge_rule_chain_set', blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'device_profile'
        unique_together = (('tenant_id', 'external_id'), ('tenant_id', 'name'),)


class Edge(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    additional_info = models.CharField(blank=True, null=True)
    customer_id = models.UUIDField(blank=True, null=True)
    root_rule_chain_id = models.UUIDField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    label = models.CharField(max_length=255, blank=True, null=True)
    routing_key = models.CharField(unique=True, max_length=255, blank=True, null=True)
    secret = models.CharField(max_length=255, blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'edge'
        unique_together = (('tenant_id', 'name'),)


class EdgeEvent(models.Model):
    seq_id = models.AutoField()
    id = models.UUIDField()
    created_time = models.BigIntegerField()
    edge_id = models.UUIDField(blank=True, null=True)
    edge_event_type = models.CharField(max_length=255, blank=True, null=True)
    edge_event_uid = models.CharField(max_length=255, blank=True, null=True)
    entity_id = models.UUIDField(blank=True, null=True)
    edge_event_action = models.CharField(max_length=255, blank=True, null=True)
    body = models.CharField(max_length=10000000, blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    ts = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'edge_event'


class EntityAlarm(models.Model):
    tenant_id = models.UUIDField()
    entity_type = models.CharField(max_length=32, blank=True, null=True)
    entity_id = models.UUIDField(primary_key=True)  # The composite primary key (entity_id, alarm_id) found, that is not supported. The first column is selected.
    created_time = models.BigIntegerField()
    alarm_type = models.CharField(max_length=255)
    customer_id = models.UUIDField(blank=True, null=True)
    alarm = models.ForeignKey(Alarm, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'entity_alarm'
        unique_together = (('entity_id', 'alarm'),)


class EntityView(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    entity_id = models.UUIDField(blank=True, null=True)
    entity_type = models.CharField(max_length=255, blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    customer_id = models.UUIDField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    keys = models.CharField(max_length=10000000, blank=True, null=True)
    start_ts = models.BigIntegerField(blank=True, null=True)
    end_ts = models.BigIntegerField(blank=True, null=True)
    additional_info = models.CharField(blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'entity_view'
        unique_together = (('tenant_id', 'external_id'),)


class ErrorEvent(models.Model):
    id = models.UUIDField()
    tenant_id = models.UUIDField()
    ts = models.BigIntegerField()
    entity_id = models.UUIDField()
    service_id = models.CharField()
    e_method = models.CharField()
    e_error = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'error_event'


class LcEvent(models.Model):
    id = models.UUIDField()
    tenant_id = models.UUIDField()
    ts = models.BigIntegerField()
    entity_id = models.UUIDField()
    service_id = models.CharField()
    e_type = models.CharField()
    e_success = models.BooleanField()
    e_error = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lc_event'


class Notification(models.Model):
    id = models.UUIDField()
    created_time = models.BigIntegerField()
    request_id = models.UUIDField(blank=True, null=True)
    recipient_id = models.UUIDField()
    type = models.CharField(max_length=50)
    delivery_method = models.CharField(max_length=50)
    subject = models.CharField(max_length=255, blank=True, null=True)
    body = models.CharField(max_length=1000)
    additional_config = models.CharField(max_length=1000, blank=True, null=True)
    status = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notification'


class NotificationRequest(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    tenant_id = models.UUIDField()
    targets = models.CharField(max_length=10000)
    template_id = models.UUIDField(blank=True, null=True)
    template = models.CharField(max_length=10000000, blank=True, null=True)
    info = models.CharField(max_length=1000000, blank=True, null=True)
    additional_config = models.CharField(max_length=1000, blank=True, null=True)
    originator_entity_id = models.UUIDField(blank=True, null=True)
    originator_entity_type = models.CharField(max_length=32, blank=True, null=True)
    rule_id = models.UUIDField(blank=True, null=True)
    status = models.CharField(max_length=32, blank=True, null=True)
    stats = models.CharField(max_length=10000, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notification_request'


class NotificationRule(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    tenant_id = models.UUIDField()
    name = models.CharField(max_length=255)
    enabled = models.BooleanField()
    template = models.ForeignKey('NotificationTemplate', models.DO_NOTHING)
    trigger_type = models.CharField(max_length=50)
    trigger_config = models.CharField(max_length=1000)
    recipients_config = models.CharField(max_length=10000)
    additional_config = models.CharField(max_length=255, blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notification_rule'
        unique_together = (('tenant_id', 'external_id'), ('tenant_id', 'name'),)


class NotificationTarget(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    tenant_id = models.UUIDField()
    name = models.CharField(max_length=255)
    configuration = models.CharField(max_length=10000)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notification_target'
        unique_together = (('tenant_id', 'external_id'), ('tenant_id', 'name'),)


class NotificationTemplate(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    tenant_id = models.UUIDField()
    name = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=50)
    configuration = models.CharField(max_length=10000000)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notification_template'
        unique_together = (('tenant_id', 'external_id'), ('tenant_id', 'name'),)


class Oauth2ClientRegistration(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    domain_name = models.CharField(max_length=255, blank=True, null=True)
    domain_scheme = models.CharField(max_length=31, blank=True, null=True)
    client_registration_info_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'oauth2_client_registration'


class Oauth2ClientRegistrationInfo(models.Model):
    id = models.UUIDField(primary_key=True)
    enabled = models.BooleanField(blank=True, null=True)
    created_time = models.BigIntegerField()
    additional_info = models.CharField(blank=True, null=True)
    client_id = models.CharField(max_length=255, blank=True, null=True)
    client_secret = models.CharField(max_length=255, blank=True, null=True)
    authorization_uri = models.CharField(max_length=255, blank=True, null=True)
    token_uri = models.CharField(max_length=255, blank=True, null=True)
    scope = models.CharField(max_length=255, blank=True, null=True)
    user_info_uri = models.CharField(max_length=255, blank=True, null=True)
    user_name_attribute_name = models.CharField(max_length=255, blank=True, null=True)
    jwk_set_uri = models.CharField(max_length=255, blank=True, null=True)
    client_authentication_method = models.CharField(max_length=255, blank=True, null=True)
    login_button_label = models.CharField(max_length=255, blank=True, null=True)
    login_button_icon = models.CharField(max_length=255, blank=True, null=True)
    allow_user_creation = models.BooleanField(blank=True, null=True)
    activate_user = models.BooleanField(blank=True, null=True)
    type = models.CharField(max_length=31, blank=True, null=True)
    basic_email_attribute_key = models.CharField(max_length=31, blank=True, null=True)
    basic_first_name_attribute_key = models.CharField(max_length=31, blank=True, null=True)
    basic_last_name_attribute_key = models.CharField(max_length=31, blank=True, null=True)
    basic_tenant_name_strategy = models.CharField(max_length=31, blank=True, null=True)
    basic_tenant_name_pattern = models.CharField(max_length=255, blank=True, null=True)
    basic_customer_name_pattern = models.CharField(max_length=255, blank=True, null=True)
    basic_default_dashboard_name = models.CharField(max_length=255, blank=True, null=True)
    basic_always_full_screen = models.BooleanField(blank=True, null=True)
    custom_url = models.CharField(max_length=255, blank=True, null=True)
    custom_username = models.CharField(max_length=255, blank=True, null=True)
    custom_password = models.CharField(max_length=255, blank=True, null=True)
    custom_send_token = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'oauth2_client_registration_info'


class Oauth2ClientRegistrationTemplate(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    additional_info = models.CharField(blank=True, null=True)
    provider_id = models.CharField(unique=True, max_length=255, blank=True, null=True)
    authorization_uri = models.CharField(max_length=255, blank=True, null=True)
    token_uri = models.CharField(max_length=255, blank=True, null=True)
    scope = models.CharField(max_length=255, blank=True, null=True)
    user_info_uri = models.CharField(max_length=255, blank=True, null=True)
    user_name_attribute_name = models.CharField(max_length=255, blank=True, null=True)
    jwk_set_uri = models.CharField(max_length=255, blank=True, null=True)
    client_authentication_method = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=31, blank=True, null=True)
    basic_email_attribute_key = models.CharField(max_length=31, blank=True, null=True)
    basic_first_name_attribute_key = models.CharField(max_length=31, blank=True, null=True)
    basic_last_name_attribute_key = models.CharField(max_length=31, blank=True, null=True)
    basic_tenant_name_strategy = models.CharField(max_length=31, blank=True, null=True)
    basic_tenant_name_pattern = models.CharField(max_length=255, blank=True, null=True)
    basic_customer_name_pattern = models.CharField(max_length=255, blank=True, null=True)
    basic_default_dashboard_name = models.CharField(max_length=255, blank=True, null=True)
    basic_always_full_screen = models.BooleanField(blank=True, null=True)
    comment = models.CharField(blank=True, null=True)
    login_button_icon = models.CharField(max_length=255, blank=True, null=True)
    login_button_label = models.CharField(max_length=255, blank=True, null=True)
    help_link = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'oauth2_client_registration_template'


class Oauth2Domain(models.Model):
    id = models.UUIDField(primary_key=True)
    oauth2_params = models.ForeignKey('Oauth2Params', models.DO_NOTHING)
    created_time = models.BigIntegerField()
    domain_name = models.CharField(max_length=255, blank=True, null=True)
    domain_scheme = models.CharField(max_length=31, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'oauth2_domain'
        unique_together = (('oauth2_params', 'domain_name', 'domain_scheme'),)


class Oauth2Mobile(models.Model):
    id = models.UUIDField(primary_key=True)
    oauth2_params = models.ForeignKey('Oauth2Params', models.DO_NOTHING)
    created_time = models.BigIntegerField()
    pkg_name = models.CharField(max_length=255, blank=True, null=True)
    app_secret = models.CharField(max_length=2048, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'oauth2_mobile'
        unique_together = (('oauth2_params', 'pkg_name'),)


class Oauth2Params(models.Model):
    id = models.UUIDField(primary_key=True)
    enabled = models.BooleanField(blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    created_time = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'oauth2_params'


class Oauth2Registration(models.Model):
    id = models.UUIDField(primary_key=True)
    oauth2_params = models.ForeignKey(Oauth2Params, models.DO_NOTHING)
    created_time = models.BigIntegerField()
    additional_info = models.CharField(blank=True, null=True)
    client_id = models.CharField(max_length=255, blank=True, null=True)
    client_secret = models.CharField(max_length=2048, blank=True, null=True)
    authorization_uri = models.CharField(max_length=255, blank=True, null=True)
    token_uri = models.CharField(max_length=255, blank=True, null=True)
    scope = models.CharField(max_length=255, blank=True, null=True)
    platforms = models.CharField(max_length=255, blank=True, null=True)
    user_info_uri = models.CharField(max_length=255, blank=True, null=True)
    user_name_attribute_name = models.CharField(max_length=255, blank=True, null=True)
    jwk_set_uri = models.CharField(max_length=255, blank=True, null=True)
    client_authentication_method = models.CharField(max_length=255, blank=True, null=True)
    login_button_label = models.CharField(max_length=255, blank=True, null=True)
    login_button_icon = models.CharField(max_length=255, blank=True, null=True)
    allow_user_creation = models.BooleanField(blank=True, null=True)
    activate_user = models.BooleanField(blank=True, null=True)
    type = models.CharField(max_length=31, blank=True, null=True)
    basic_email_attribute_key = models.CharField(max_length=31, blank=True, null=True)
    basic_first_name_attribute_key = models.CharField(max_length=31, blank=True, null=True)
    basic_last_name_attribute_key = models.CharField(max_length=31, blank=True, null=True)
    basic_tenant_name_strategy = models.CharField(max_length=31, blank=True, null=True)
    basic_tenant_name_pattern = models.CharField(max_length=255, blank=True, null=True)
    basic_customer_name_pattern = models.CharField(max_length=255, blank=True, null=True)
    basic_default_dashboard_name = models.CharField(max_length=255, blank=True, null=True)
    basic_always_full_screen = models.BooleanField(blank=True, null=True)
    custom_url = models.CharField(max_length=255, blank=True, null=True)
    custom_username = models.CharField(max_length=255, blank=True, null=True)
    custom_password = models.CharField(max_length=255, blank=True, null=True)
    custom_send_token = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'oauth2_registration'


class OtaPackage(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    tenant_id = models.UUIDField()
    device_profile = models.ForeignKey(DeviceProfile, models.DO_NOTHING, blank=True, null=True)
    type = models.CharField(max_length=32)
    title = models.CharField(max_length=255)
    version = models.CharField(max_length=255)
    tag = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    content_type = models.CharField(max_length=255, blank=True, null=True)
    checksum_algorithm = models.CharField(max_length=32, blank=True, null=True)
    checksum = models.CharField(max_length=1020, blank=True, null=True)
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    data_size = models.BigIntegerField(blank=True, null=True)
    additional_info = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ota_package'
        unique_together = (('tenant_id', 'title', 'version'),)


class Queue(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    tenant_id = models.UUIDField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    topic = models.CharField(max_length=255, blank=True, null=True)
    poll_interval = models.IntegerField(blank=True, null=True)
    partitions = models.IntegerField(blank=True, null=True)
    consumer_per_partition = models.BooleanField(blank=True, null=True)
    pack_processing_timeout = models.BigIntegerField(blank=True, null=True)
    submit_strategy = models.CharField(max_length=255, blank=True, null=True)
    processing_strategy = models.CharField(max_length=255, blank=True, null=True)
    additional_info = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'queue'


class Relation(models.Model):
    from_id = models.UUIDField(primary_key=True)  # The composite primary key (from_id, from_type, relation_type_group, relation_type, to_id, to_type) found, that is not supported. The first column is selected.
    from_type = models.CharField(max_length=255)
    to_id = models.UUIDField()
    to_type = models.CharField(max_length=255)
    relation_type_group = models.CharField(max_length=255)
    relation_type = models.CharField(max_length=255)
    additional_info = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'relation'
        unique_together = (('from_id', 'from_type', 'relation_type_group', 'relation_type', 'to_id', 'to_type'),)


class Resource(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    tenant_id = models.UUIDField()
    title = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=32)
    resource_key = models.CharField(max_length=255)
    search_text = models.CharField(max_length=255, blank=True, null=True)
    file_name = models.CharField(max_length=255)
    data = models.BinaryField(blank=True, null=True)
    etag = models.CharField(blank=True, null=True)
    descriptor = models.CharField(blank=True, null=True)
    preview = models.BinaryField(blank=True, null=True)
    is_public = models.BooleanField(blank=True, null=True)
    public_resource_key = models.CharField(unique=True, max_length=32, blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resource'
        unique_together = (('tenant_id', 'resource_type', 'resource_key'),)


class Rpc(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    tenant_id = models.UUIDField()
    device_id = models.UUIDField()
    expiration_time = models.BigIntegerField()
    request = models.CharField(max_length=10000000)
    response = models.CharField(max_length=10000000, blank=True, null=True)
    additional_info = models.CharField(max_length=10000000, blank=True, null=True)
    status = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'rpc'


class RuleChain(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    additional_info = models.CharField(blank=True, null=True)
    configuration = models.CharField(max_length=10000000, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    first_rule_node_id = models.UUIDField(blank=True, null=True)
    root = models.BooleanField(blank=True, null=True)
    debug_mode = models.BooleanField(blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rule_chain'
        unique_together = (('tenant_id', 'external_id'),)


class RuleChainDebugEvent(models.Model):
    id = models.UUIDField()
    tenant_id = models.UUIDField()
    ts = models.BigIntegerField()
    entity_id = models.UUIDField()
    service_id = models.CharField()
    e_message = models.CharField(blank=True, null=True)
    e_error = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rule_chain_debug_event'


class RuleNode(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    rule_chain_id = models.UUIDField(blank=True, null=True)
    additional_info = models.CharField(blank=True, null=True)
    configuration_version = models.IntegerField(blank=True, null=True)
    configuration = models.CharField(max_length=10000000, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    debug_mode = models.BooleanField(blank=True, null=True)
    singleton_mode = models.BooleanField(blank=True, null=True)
    queue_name = models.CharField(max_length=255, blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rule_node'


class RuleNodeDebugEvent(models.Model):
    id = models.UUIDField()
    tenant_id = models.UUIDField()
    ts = models.BigIntegerField()
    entity_id = models.UUIDField()
    service_id = models.CharField(blank=True, null=True)
    e_type = models.CharField(blank=True, null=True)
    e_entity_id = models.UUIDField(blank=True, null=True)
    e_entity_type = models.CharField(blank=True, null=True)
    e_msg_id = models.UUIDField(blank=True, null=True)
    e_msg_type = models.CharField(blank=True, null=True)
    e_data_type = models.CharField(blank=True, null=True)
    e_relation_type = models.CharField(blank=True, null=True)
    e_data = models.CharField(blank=True, null=True)
    e_metadata = models.CharField(blank=True, null=True)
    e_error = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rule_node_debug_event'


class RuleNodeState(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    rule_node = models.ForeignKey(RuleNode, models.DO_NOTHING)
    entity_type = models.CharField(max_length=32)
    entity_id = models.UUIDField()
    state_data = models.CharField(max_length=16384)

    class Meta:
        managed = False
        db_table = 'rule_node_state'
        unique_together = (('rule_node', 'entity_id'),)


class StatsEvent(models.Model):
    id = models.UUIDField()
    tenant_id = models.UUIDField()
    ts = models.BigIntegerField()
    entity_id = models.UUIDField()
    service_id = models.CharField()
    e_messages_processed = models.BigIntegerField()
    e_errors_occurred = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'stats_event'


class TbSchemaSettings(models.Model):
    schema_version = models.BigIntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = 'tb_schema_settings'


class TbUser(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    additional_info = models.CharField(blank=True, null=True)
    authority = models.CharField(max_length=255, blank=True, null=True)
    customer_id = models.UUIDField(blank=True, null=True)
    email = models.CharField(unique=True, max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tb_user'


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    additional_info = models.CharField(blank=True, null=True)
    tenant_profile = models.ForeignKey('TenantProfile', models.DO_NOTHING)
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
        managed = False
        db_table = 'tenant'


class TenantProfile(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    name = models.CharField(unique=True, max_length=255, blank=True, null=True)
    profile_data = models.JSONField(blank=True, null=True)
    description = models.CharField(blank=True, null=True)
    is_default = models.BooleanField(blank=True, null=True)
    isolated_tb_core = models.BooleanField(blank=True, null=True)
    isolated_tb_rule_engine = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tenant_profile'


class TsKv(models.Model):
    entity_id = models.UUIDField(primary_key=True)  # The composite primary key (entity_id, key, ts) found, that is not supported. The first column is selected.
    key = models.IntegerField()
    ts = models.BigIntegerField()
    bool_v = models.BooleanField(blank=True, null=True)
    str_v = models.CharField(max_length=10000000, blank=True, null=True)
    long_v = models.BigIntegerField(blank=True, null=True)
    dbl_v = models.FloatField(blank=True, null=True)
    json_v = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'ts_kv'
        unique_together = (('entity_id', 'key', 'ts'),)


class TsKvDictionary(models.Model):
    key = models.CharField(primary_key=True, max_length=255)
    key_id = models.AutoField(unique=True)

    class Meta:
        managed = False
        db_table = 'ts_kv_dictionary'


class TsKvLatest(models.Model):
    entity_id = models.UUIDField(primary_key=True)  # The composite primary key (entity_id, key) found, that is not supported. The first column is selected.
    key = models.IntegerField()
    ts = models.BigIntegerField()
    bool_v = models.BooleanField(blank=True, null=True)
    str_v = models.CharField(max_length=10000000, blank=True, null=True)
    long_v = models.BigIntegerField(blank=True, null=True)
    dbl_v = models.FloatField(blank=True, null=True)
    json_v = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'ts_kv_latest'
        unique_together = (('entity_id', 'key'),)


class UserAuthSettings(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    user = models.OneToOneField(TbUser, models.DO_NOTHING)
    two_fa_settings = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_auth_settings'


class UserCredentials(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    activate_token = models.CharField(unique=True, max_length=255, blank=True, null=True)
    enabled = models.BooleanField(blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    reset_token = models.CharField(unique=True, max_length=255, blank=True, null=True)
    user_id = models.UUIDField(unique=True, blank=True, null=True)
    additional_info = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_credentials'


class UserSettings(models.Model):
    user = models.OneToOneField(TbUser, models.DO_NOTHING, primary_key=True)  # The composite primary key (user_id, type) found, that is not supported. The first column is selected.
    type = models.CharField(max_length=50)
    settings = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_settings'
        unique_together = (('user', 'type'),)


class WidgetType(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    fqn = models.CharField(max_length=512, blank=True, null=True)
    descriptor = models.CharField(max_length=1000000, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    image = models.CharField(max_length=1000000, blank=True, null=True)
    deprecated = models.BooleanField()
    description = models.CharField(max_length=1024, blank=True, null=True)
    tags = models.TextField(blank=True, null=True)  # This field type is a guess.
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'widget_type'
        unique_together = (('tenant_id', 'fqn'), ('tenant_id', 'external_id'),)


class WidgetsBundle(models.Model):
    id = models.UUIDField(primary_key=True)
    created_time = models.BigIntegerField()
    alias = models.CharField(max_length=255, blank=True, null=True)
    tenant_id = models.UUIDField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    image = models.CharField(max_length=1000000, blank=True, null=True)
    description = models.CharField(max_length=1024, blank=True, null=True)
    widgets_bundle_order = models.IntegerField(blank=True, null=True)
    external_id = models.UUIDField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'widgets_bundle'
        unique_together = (('tenant_id', 'alias'), ('tenant_id', 'external_id'),)


class WidgetsBundleWidget(models.Model):
    widgets_bundle = models.OneToOneField(WidgetsBundle, models.DO_NOTHING, primary_key=True)  # The composite primary key (widgets_bundle_id, widget_type_id) found, that is not supported. The first column is selected.
    widget_type = models.ForeignKey(WidgetType, models.DO_NOTHING)
    widget_type_order = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'widgets_bundle_widget'
        unique_together = (('widgets_bundle', 'widget_type'),)
