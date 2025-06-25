import json

from django.core.management.base import BaseCommand

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        ch = connect_to_rabbitmq()

        with open("output_500.json", "r") as f:
            msg = json.load(f)
            attrs = [m for m in msg if m.get("topic").endswith("/attributes")]
            print(len(attrs))
            for m in attrs:
                send_to_rabbitmq(ch, m, "/attributes")

            msg = [m for m in msg if m.get("topic").endswith("/telemetry")]
            print(len(msg))
            for m in msg:
                send_to_rabbitmq(ch, m, "/telemetry")
