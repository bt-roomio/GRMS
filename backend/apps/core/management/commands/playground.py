from django.core.management.base import BaseCommand
from django.db.models import Case, F, IntegerField, JSONField, Prefetch, Q, TextField, Value, When
from django.db.models.functions import Cast, Coalesce

from core.utils.query_debugger import query_debugger
from main.models import Device, Room
from shuttle.models import AttributeKv, TsKvLatest


class Command(BaseCommand):
    help = "Playground"

    @query_debugger
    def handle(self, *args, **options):
        data = [
            {"name": "active", "tag_type": "attribute", "attribute_scope": "SERVER_SCOPE"},
            {"name": "roomNumber", "tag_type": "attribute", "attribute_scope": "SHARED_SCOPE"},
        ]

        attrs_filters = Q()
        for item in data:
            attrs_filters |= Q(attribute_key=item["name"], attribute_type=item["attribute_scope"])
        ts_kvs_keys = ["MUR Relay", "Window", "Room Temperature"]

        # query = Room.objects.filter(active=True, tenant_id="28c81921-f78e-4864-87d2-cec674f19d1c")
        rooms = Room.objects.filter(number="106", active=True)

        rooms = rooms.prefetch_related(
            Prefetch(
                "devices",
                queryset=Device.objects.annotate(
                    priority=Case(
                        When(additional_info__primary=True, then=Value(0)),
                        default=Value(1),
                        output_field=IntegerField(),
                    )
                )
                .order_by("priority", "created_at")
                .prefetch_related(
                    Prefetch(
                        "attribute_kvs",
                        queryset=AttributeKv.objects.filter(attrs_filters).annotate(
                            value=Coalesce(
                                Cast("bool_v", TextField()),
                                Cast("str_v", TextField()),
                                Cast("dbl_v", TextField()),
                                Cast("long_v", TextField()),
                                Cast("json_v", TextField()),
                                output_field=TextField(),
                            )
                        ),
                        to_attr="attrs",
                    ),
                    Prefetch(
                        "attribute_kvs",
                        queryset=TsKvLatest.objects.prefetch_related("key")
                        .filter(key__key__in=ts_kvs_keys)
                        .annotate(
                            value=Coalesce(
                                Cast("bool_v", TextField()),
                                Cast("str_v", TextField()),
                                Cast("dbl_v", TextField()),
                                Cast("long_v", TextField()),
                                Cast("json_v", TextField()),
                                output_field=TextField(),
                            )
                        ),
                        to_attr="ts_kvs",
                    ),
                ),
                to_attr="room_devices",
            )
        ).order_by("number")

        # Берем первое устройство (с наивысшим приоритетом)
        for room in rooms:
            target_device = room.room_devices[0] if room.room_devices else None
            room.attributes = target_device.attrs if target_device else []
            room.ts_kvs = target_device.ts_kvs if target_device else []

        # Используем
        for room in rooms:
            print(f"\n=== Room: {room.id, room.number} ===")
            for attr in room.attributes:
                print(f"  {attr.attribute_key} = {attr.value}, {attr.entity_id}")
            for ts_kv in room.ts_kvs:
                print(f"  {ts_kv.key.key} = {ts_kv.value}, {ts_kv.entity_id}")

        # # Filter by attribute_type and attribute_key
        # # 1. For one room, multiple attributes
        # entity_id = "02fce171-ca93-4d67-9cc8-7cedfbdb043e"
        # filters = Q()
        # for item in data:
        #     filters |= Q(attribute_key=item["name"], attribute_type=item["attribute_scope"])
        # attrs = AttributeKv.objects.filter(filters & Q(entity_id=entity_id))
        # for attr in attrs:
        #     print(attr.attribute_key, attr.attribute_type, attr.entity_id, attr.long_v)
