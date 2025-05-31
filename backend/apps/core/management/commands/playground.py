from django.core.management.base import BaseCommand
from django.db.models import OuterRef, Subquery

from main.models import Room
from shuttle.models import TsKvLatest


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        temp_subq = (
            TsKvLatest.objects.filter(entity__room=OuterRef("pk"), key__key="Room Temperature")
            .order_by()
            .values("long_v")[:1]
        )
        mur_subq = (
            TsKvLatest.objects.filter(entity__room=OuterRef("pk"), key__key="MUR Relay").order_by().values("long_v")[:1]
        )

        rooms = (
            Room.objects.prefetch_related("devices__ts_kvs_latest__key")
            .filter(tenant_id="ac73203f-e25f-4baa-a5c7-a4c9585f5bbc", devices__isnull=False)
            .annotate(temperature=Subquery(temp_subq), mur=Subquery(mur_subq))
        )
        for room in rooms:
            print(room.id, room.temperature, room.mur)
        #     r = rooms.ts_kvs_latest_values(
        #         ["MUR Relay", "DND Relay", "AC_ON_OFF", "Room Temperature", "Occupancy State"]
        #     )
        #     print(r)
