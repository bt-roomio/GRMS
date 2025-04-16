import logging
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.utils.get_time import get_mil_sec
from core.utils.read_cpu_ram import get_cpu_usage, get_disk_usage, get_ram_usage
from main.models import Device, DeviceProfile, Tenant
from shuttle.models import TsKv, TsKvDictionary, TsKvLatest

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        while True:
            cpu_ram_save_db()
            time.sleep(10)


def cpu_ram_save_db():
    def_tenant = Tenant.objects.filter(title__iexact="Default").first()
    if not def_tenant:
        logger.warning("There are not Default tenant!")
        return

    print("Saving CPU RAM Usage to DB", timezone.now())
    keys = {"cpuUsage": get_cpu_usage(), "memoryUsage": get_ram_usage(), "diskUsage": get_disk_usage()}
    profile_device, _ = DeviceProfile.objects.get_or_create(name="Default", tenant=def_tenant, type="DEFAULT")
    device, _ = Device.objects.get_or_create(
        name="CPU RAM Usage",
        is_active=True,
        tenant=def_tenant,
        type="DEFAULT",
        device_profile=profile_device,
    )

    for key, value in keys.items():
        ts_kv_dict, _ = TsKvDictionary.objects.get_or_create(key=key)
        TsKvLatest.objects.update_or_create(
            entity=device, key=ts_kv_dict, defaults={"dbl_v": value, "ts": get_mil_sec()}
        )

        last_ts_kv = TsKv.objects.filter(key=ts_kv_dict, entity=device)
        last_ts_kv = last_ts_kv.first() if not last_ts_kv else last_ts_kv.latest("ts")

        if not last_ts_kv or last_ts_kv.dbl_v != value:
            TsKv.objects.create(key=ts_kv_dict, dbl_v=value, ts=timezone.now, entity=device)
