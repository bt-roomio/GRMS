from uuid import UUID

from django.core.management.base import BaseCommand

from main.models import Device
from shuttle.models import Relation


class Command(BaseCommand):
    help = "Create Relation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Skip confirmation prompt (use with caution)",
        )
        parser.add_argument(
            "tenant_id",
            type=UUID,
            help="Tenant",
        )

    def handle(self, *args, **options):
        """Create Relation between gateway and other devices"""
        tenant_id = options["tenant_id"]
        confirm = options["confirm"]

        is_gateway = Device.objects.filter(tenant_id=tenant_id, is_active=True, additional_info__gateway=True).first()
        devices = Device.objects.filter(tenant_id=tenant_id, is_active=True).exclude(
            id=is_gateway.id  # pyright: ignore
        )

        print(
            f"Tenant: {tenant_id}, {devices.count()} device count will be connected to `{is_gateway.name}`"  # pyright: ignore
        )
        if not confirm:
            return

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

        print("Successfully created relations")
