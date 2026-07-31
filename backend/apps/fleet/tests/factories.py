"""Object factories shared by the fleet tests and the shuttle consumer tests."""

import uuid

from asgiref.sync import sync_to_async

from fleet.models import FleetNode
from main.models import Device, DeviceProfile, Tenant, TenantProfile

SSH_USER = "roomio-agent"


def create_tenant(title="Fleet Test"):
    unique = uuid.uuid4().hex[:8]
    profile = TenantProfile.objects.create(name=f"fleet-test-profile-{unique}")
    return Tenant.objects.create(title=title, tenant_profile=profile)


def create_gateway(tenant, name=None, **overrides):
    """A Device flagged as a gateway — what a FleetNode must point at."""
    unique = uuid.uuid4().hex[:8]
    profile = DeviceProfile.objects.create(name=f"gw-profile-{unique}", type="default", tenant=tenant)
    fields = {
        "name": name or f"gw-{unique}",
        "type": "gateway",
        "tenant": tenant,
        "device_profile": profile,
        "additional_info": {"gateway": True},
    }
    fields.update(overrides)
    return Device.objects.create(**fields)


def create_node(**overrides):
    unique = uuid.uuid4().hex[:8]
    tenant = overrides.pop("tenant", None) or create_tenant()
    gateway = overrides.pop("gateway", None) or create_gateway(tenant)

    fields = {
        "tenant": tenant,
        "gateway": gateway,
        "code": f"fleet-test_{unique}",
        "mesh_ip": "127.0.0.1",
        "ssh_user": SSH_USER,
    }
    fields.update(overrides)
    return FleetNode.objects.create(**fields)


make_node = sync_to_async(create_node)
