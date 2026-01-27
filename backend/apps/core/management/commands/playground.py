from django.core.management.base import BaseCommand

from core.management.mq.get_device import DeviceType, get_sub_device
from main.models import Device, DeviceProfile


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        device = Device.objects.get(id="484f368a-5065-4d1c-bfec-89b53ed9faa8")
        data: DeviceType = {
            "id": str(device.id),
            "name": device.name,
            "tenant_id": str(device.tenant_id),
            "device_profile_id": str(device.device_profile_id),
        }
        get_sub_device(data, name="Test Subdevice 1", device_type="TTLock")
