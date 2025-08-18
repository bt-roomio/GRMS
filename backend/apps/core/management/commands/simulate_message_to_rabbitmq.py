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
        msg = {
            "sourceDeviceUUID": "4b6ab65b-8cc5-44f3-b45c-312d5254cb86",
            "data": {
                # "38:0c:6e:41:02:80": {
                "bc:e3:5c:0e:d3:e4": {
                    # "macAddress": "04:60:e8:78:d3:e4",
                    # If telemetry
                    "ts": 1749978215719,
                    "values": {
                        "DND Relay": 0,
                    },
                }
            },
            "topic": "v1/gateway/telemetry",
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
