from django.core.management.base import BaseCommand

from core.management.mq.get_device import get_or_create_device
from core.utils.date import convert_datetime
from main.models import Device
from shuttle.utils.datetime_aware import to_datetime_aware


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        value = 1766523600000
        r = to_datetime_aware(value)
        # r = convert_datetime(value)
        print(r)
        return

        device = Device.objects.get(id="01efd4c4-0b84-49ee-be29-61b8fbb3d8ba")
        gateway = {
            "id": str(device.id),
            "name": device.name,
            "tenant_id": str(device.tenant_id),
            "device_profile_id": str(device.device_profile_id),
        }

        get_or_create_device("1a:9c:48:d7:40:92", gateway)
