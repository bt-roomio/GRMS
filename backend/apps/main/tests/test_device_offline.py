from django.test import TestCase

from main.metrics import offline_gateway_devices_simple, update_device_metrics
from main.models import Device, DeviceProfile, Tenant, TenantProfile


class DeviceMetricsTestCase(TestCase):
    def setUp(self):
        tenant_profile = TenantProfile.objects.create(name="Test Profile", is_default=True)
        self.tenant = Tenant.objects.create(title="Test Tenant", tenant_profile=tenant_profile)

    def test_offline_gateway_metric(self):
        # Create an offline gateway device
        device_profile = DeviceProfile.objects.create(name="Gateway Profile", tenant=self.tenant, type="Default")
        Device.objects.create(
            name="Gateway 1",
            type="gateway",
            tenant=self.tenant,
            status=False,
            additional_info={"gateway": True},
            device_profile=device_profile,  # Assuming you have a profile
        )

        # Create an online gateway device (should not be counted)
        Device.objects.create(
            name="Gateway 2",
            type="gateway",
            tenant=self.tenant,
            status=True,
            additional_info={"gateway": True},
            device_profile=device_profile,
        )

        # Create an offline non-gateway device (should not be counted)
        Device.objects.create(
            name="Device 3",
            type="sensor",
            tenant=self.tenant,
            status=False,
            additional_info={"gateway": False},
            device_profile=device_profile,
        )

        # Update metrics
        update_device_metrics()

        # Check the metric value
        self.assertEqual(offline_gateway_devices_simple._value.get(), 1)
        self.assertNotEqual(offline_gateway_devices_simple._value.get(), 2)
