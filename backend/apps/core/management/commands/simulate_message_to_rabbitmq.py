from django.core.management.base import BaseCommand

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        msg = {
            "sourceDeviceUUID": "c6fe44a3-b349-491d-bd7b-31c32dcaf3db",
            "data": {"40:76:2E:18:DB:32": [{"ts": 1748328532448, "values": {"Occupancy State": 0}}]},
            "topic": "v1/gateway/telemetry",
        }
        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, msg, "toGRMS")
