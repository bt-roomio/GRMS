from django.core.management.base import BaseCommand

from main.models import Device
from shuttle.models import Relation


class Command(BaseCommand):
    help = "Create Relation"

    def handle(self, *args, **options):
        """Create Relation between gateway and other devices"""

        tenant_id = "ea776673-3987-429f-b969-e9afb606dc8c"

        is_gateway = Device.objects.filter(tenant_id=tenant_id, is_active=True, additional_info__gateway=True).first()
        devices = Device.objects.filter(tenant_id=tenant_id, is_active=True).exclude(
            id=is_gateway.id  # pyright: ignore
        )

        print(devices.count())

        for device in devices:
            dd = {
                "from_id": is_gateway,
                "from_type": "DEVICE",
                "relation_type_group": "COMMON",
                "relation_type": "Created",
                "to_id": device,
                "to_type": "DEVICE",
            }
            Relation.objects.get_or_create(**dd)
