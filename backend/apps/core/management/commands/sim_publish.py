from django.core.management.base import BaseCommand
from django.utils import timezone

from shuttle.services.ts_kv_latest import publish_updates_batch


class Command(BaseCommand):
    help = "Simulate publish updates"

    def handle(self, *args, **options):
        device_id = "00136d0a-f59b-4049-a35d-01bf86b07d3e"
        tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
        value = 22.5
        field = "dbl_v"
        key = f"{device_id}_{tenant_id}"
        updates_by_device = {key: []}
        updates_by_device[key].append(
            {
                "entity": str(device_id),
                "key": "Room Temperature",
                "ts": timezone.now(),
                "bool_v": value if field == "bool_v" else None,
                "str_v": value if field == "str_v" else None,
                "long_v": value if field == "long_v" else None,
                "dbl_v": value if field == "dbl_v" else None,
                "json_v": value if field == "json_v" else None,
            }
        )
        publish_updates_batch(updates_by_device)
