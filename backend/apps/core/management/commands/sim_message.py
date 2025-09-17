import time

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
            "sourceDeviceUUID": "5aab4f30-3e46-4ae5-9200-0ec6f51aa344",
            "data": {
                "38:0c:6e:41:02:80": {
                    # "bc:e3:5c:0e:d3:e4": {
                    # "macAddress": "04:60:e8:78:d3:e4",
                    # If telemetry
                    "ts": time.time(),
                    "values": {
                        "Window": 0,
                    },
                }
            },
            "topic": "v1/gateway/telemetry",
        }
        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, msg, "toGRMS")
