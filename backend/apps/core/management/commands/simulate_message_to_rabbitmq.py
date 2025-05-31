from django.core.management.base import BaseCommand

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        msg = {
            "sourceDeviceUUID": "c6fe44a3-b349-491d-bd7b-31c32dcaf3db",
            "data": {"64:61:D6:63:56:C9": [{"ts": 1748328532448, "values": {"DND Relay": 1}}]},
            "topic": "v1/gateway/telemetry",
        }
        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, msg, "toGRMS")
