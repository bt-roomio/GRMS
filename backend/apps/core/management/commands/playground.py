from django.core.management.base import BaseCommand

from core.utils.get_time import get_mil_sec
from main.models import Device
from shuttle.tasks import publish_updates_batch_task

SIMULATED_TELEMETRY = {
    "MUR Relay": ("bool_v", True),
    "DND Relay": ("bool_v", False),
    "AC ON OFF": ("bool_v", True),
    "Room Temperature": ("dbl_v", 22.5),
    "Occupancy State": ("bool_v", True),
}


class Command(BaseCommand):
    help = "Playground — симуляция publish_updates_batch_task"

    def add_arguments(self, parser):
        parser.add_argument(
            "--device",
            type=str,
            default=None,
            help="UUID устройства (по умолчанию — первое активное устройство из БД)",
        )

    def handle(self, *args, **options):
        device_id_arg = options.get("device")

        if device_id_arg:
            device = Device.objects.filter(pk=device_id_arg).first()
        else:
            device = Device.objects.filter(is_active=True).first()

        if not device:
            self.stdout.write(self.style.ERROR("Устройство не найдено"))
            return

        device_id = str(device.id)
        tenant_id = str(device.tenant_id)
        ts_now = get_mil_sec()

        updates = []
        for key, (field, value) in SIMULATED_TELEMETRY.items():
            updates.append(
                {
                    "entity": device_id,
                    "key": key,
                    "ts": ts_now,
                    "bool_v": value if field == "bool_v" else None,
                    "str_v": value if field == "str_v" else None,
                    "long_v": value if field == "long_v" else None,
                    "dbl_v": value if field == "dbl_v" else None,
                    "json_v": value if field == "json_v" else None,
                    "value": value,
                }
            )

        updates_by_device = {f"{device_id}_{tenant_id}": updates}

        self.stdout.write(f"device_id : {device_id}")
        self.stdout.write(f"tenant_id : {tenant_id}")
        self.stdout.write(f"updates   : {len(updates)} ключ(ей)")
        for u in updates:
            self.stdout.write(f"  key={u['key']}  value={u['value']}")

        publish_updates_batch_task.delay(updates_by_device)

        self.stdout.write(self.style.SUCCESS("publish_updates_batch_task отправлена в Celery"))
