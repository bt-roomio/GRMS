import time

from django.core.management.base import BaseCommand

from core.utils.read_cpu_ram import get_cpu_usage, get_ram_usage, get_disk_usage
from main.models import Device
from shuttle.models import TsKvDictionary, TsKvLatest, TsKv


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        while True:
            print("Saving CPU RAM Usage to DB", time.time())
            cpu_ram_save_db()
            time.sleep(10)


def cpu_ram_save_db():
    keys = {"cpuUsage": get_cpu_usage(), "memoryUsage": get_ram_usage(), "diskUsage": get_disk_usage()}
    device, _ = Device.objects.get_or_create(name="CPU RAM Usage", is_active=True)

    for key, value in keys.items():
        ts_kv_dict, _ = TsKvDictionary.objects.get_or_create(key=key)
        TsKvLatest.objects.update_or_create(
            entity=device, key=ts_kv_dict.key_id, defaults={"dbl_v": value, "ts": int(time.time())}
        )

        last_ts_kv = TsKv.objects.filter(key=ts_kv_dict.key_id, entity=device)
        last_ts_kv = last_ts_kv.first() if not last_ts_kv else last_ts_kv.latest("ts")

        if not last_ts_kv or last_ts_kv.dbl_v != value:
            TsKv.objects.create(key=ts_kv_dict.key_id, dbl_v=value, ts=int(time.time()), entity=device)
