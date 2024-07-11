import time

from django.core.management.base import BaseCommand
from main.models import Device
from shuttle.models import TsKv, TsKvDictionary, TsKvLatest
from shuttle.utils.read_cpu_ram import get_cpu_usage, get_ram_usage


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        cpu_ram = (get_cpu_usage(), get_ram_usage())
        keys = ["cpuUsage", "memoryUsage"]
        entity_id = Device.objects.filter(name="CPU RAM Usage").first().id
        if entity_id is None:
            print("Entity not found")
            return
        for index in range(2):
            ts_kv_dict = TsKvDictionary.objects.filter(key=keys[index]).first()
            TsKvLatest.objects.update_or_create(
                entity_id=entity_id, key=ts_kv_dict.key_id, defaults={"dbl_v": cpu_ram[index], "ts": int(time.time())}
            )

            TsKv.objects.create(key=ts_kv_dict.key_id, dbl_v=cpu_ram[index], ts=int(time.time()), entity_id=entity_id)
