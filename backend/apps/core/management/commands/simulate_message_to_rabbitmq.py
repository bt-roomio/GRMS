import json

from django.core.management.base import BaseCommand

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq


class Command(BaseCommand):
    help = "simulate_message_to_rabbitmq"

    def add_arguments(self, parser):
        parser.add_argument(
            "--value",
            type=str,
            help="Queue name",
            default="v1/devices/me/attributes/request",
        )

    def handle(self, *args, **kwargs):
        val = kwargs["value"]

        msg = {
            "sourceDeviceUUID": "5aab4f30-3e46-4ae5-9200-0ec6f51aa344",
            "data": {
                "38:0c:6e:41:02:80": {
                    "card_uid": "10.10.214.251",
                }
            },
            "topic": "v1/gateway/attributes",
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
