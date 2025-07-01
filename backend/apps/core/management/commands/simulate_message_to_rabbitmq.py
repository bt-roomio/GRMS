import json

from django.core.management.base import BaseCommand

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq


class Command(BaseCommand):
    help = "simulate_message_to_rabbitmq"

    def handle(self, **_):
        msg = {
            "sourceDeviceUUID": "c6fe44a3-b349-491d-bd7b-31c32dcaf3db",
            "data": {"device": "d8:9c:e4:6a:bb:b3"},
            "topic": "v1/gateway/disconnect",
        }
        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, msg, "toGRMS")
        return

        with open("output_500.json", "r") as f:
            msg = json.load(f)
            attrs = [m for m in msg if m.get("topic").endswith("/attributes")]
            print(len(attrs))
            for m in attrs:
                if m.get("topic").endswith("/telemetry"):
                    send_to_rabbitmq(ch, m, "/telemetry")
                elif m.get("topic").endswith("/attributes"):
                    send_to_rabbitmq(ch, m, "/attributes")
                elif m.get("topic") == "v1/devices/me/attributes/request":
                    send_to_rabbitmq(ch, m, "v1/devices/me/attributes/request")
                elif m.get("topic") == "v1/gateway/attributes/request":
                    send_to_rabbitmq(ch, m, "v1/gateway/attributes/request")
                elif m.get("topic") == "v1/gateway/rpc":
                    send_to_rabbitmq(ch, m, "v1/gateway/rpc")
                else:
                    send_to_rabbitmq(ch, m, "toGRMS")
