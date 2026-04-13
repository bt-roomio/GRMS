from django.core.management.base import BaseCommand

from main.models import Device
from shuttle.models import AttributeKv


class Command(BaseCommand):
    help = "Change attrs"

    def handle(self, **_): ...

    @staticmethod
    def mass_give_room_number():
        for_this_tenant = "10fc05a2-9b48-40df-93dd-b914b4191a19"

        dd = Device.objects.filter(tenant_id=for_this_tenant, room__isnull=False)
        attrs = [
            AttributeKv(
                entity_id=d.id,
                attribute_type=AttributeKv.SHARED_SCOPE,
                attribute_key="roomNumber",
                str_v=d.room.number,
            )
            for d in dd
        ]
        AttributeKv.objects.bulk_create(attrs, ignore_conflicts=True)
