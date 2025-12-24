from django.core.management.base import BaseCommand
from django.utils import timezone

from core.utils.get_time import get_mil_sec
from shuttle.models import AttributeKv, TsKvDictionary, TsKvLatest
from shuttle.services.attribute_kv import publish_updates_attribute_batch
from shuttle.services.ts_kv_latest import publish_updates_batch


class Command(BaseCommand):
    help = "Simulate publish updates"

    def add_arguments(self, parser):
        parser.add_argument(
            "--value",
            type=int,
            help="value",
            default=1,
        )

    def handle(self, *args, **options):
        value = options["value"]
        # telemetry("Balcony Door", value)
        attributes(value)


def telemetry(tag="Window", value=1):
    device_id = "00136d0a-f59b-4049-a35d-01bf86b07d3e"
    tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
    field = "long_v"
    key = f"{device_id}_{tenant_id}"
    update_ts_kv_latets(tag, device_id, value, field)
    update_ts_kv_latets("Temperature", device_id, value, field)
    updates_by_device = {key: []}
    updates_by_device[key] = [
        {
            "entity": str(device_id),
            "key": tag,
            "ts": timezone.now(),
            "bool_v": value if field == "bool_v" else None,
            "str_v": value if field == "str_v" else None,
            "long_v": value if field == "long_v" else None,
            "dbl_v": value if field == "dbl_v" else None,
            "json_v": value if field == "json_v" else None,
            "value": value,
        },
        {
            "entity": str(device_id),
            "key": "Temperature",
            "ts": timezone.now(),
            "bool_v": value if field == "bool_v" else None,
            "str_v": value if field == "str_v" else None,
            "long_v": value if field == "long_v" else None,
            "dbl_v": value if field == "dbl_v" else None,
            "json_v": value if field == "json_v" else None,
            "value": value,
        },
    ]
    publish_updates_batch(updates_by_device)


def update_ts_kv_latets(tag, device_id, value, field="long_v"):
    key, _ = TsKvDictionary.objects.get_or_create(key=tag)
    TsKvLatest.objects.update_or_create(
        entity_id=device_id,
        key_id=key.key_id,
        defaults={
            "long_v": value if field == "long_v" else None,
            "bool_v": value if field == "bool_v" else None,
            "str_v": value if field == "str_v" else None,
            "dbl_v": value if field == "dbl_v" else None,
            "json_v": value if field == "json_v" else None,
            "ts": get_mil_sec(),
        },
    )


def attributes(value):
    updates_by_device = {}
    device_id = "00136d0a-f59b-4049-a35d-01bf86b07d3e"
    device = {"id": device_id, "tenant_id": "28c81921-f78e-4864-87d2-cec674f19d1c"}
    key = f"{device_id}_{device.get("tenant_id")}"
    updates_by_device[key] = []
    ts_now = get_mil_sec()
    fields = ["bool_v", "str_v", "dbl_v", "long_v", "json_v"]

    attr, _ = AttributeKv.objects.update_or_create(
        entity_id=device["id"],
        entity_type="DEVICE",
        attribute_type=AttributeKv.SHARED_SCOPE,
        attribute_key="dnd",
        defaults={
            "long_v": value,
        },
    )

    updates_by_device[key].append(
        {
            "entity": str(device_id),
            "key_name": attr.attribute_key,
            "last_update_ts": ts_now,
            "scope": attr.attribute_type,
            "value": next((getattr(attr, field) for field in fields if getattr(attr, field) is not None), None),
        }
    )

    publish_updates_attribute_batch(updates_by_device)
