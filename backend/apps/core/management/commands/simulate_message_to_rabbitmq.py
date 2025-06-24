import json

from django.core.management.base import BaseCommand

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        ch = connect_to_rabbitmq()

        with open("output.json", "r") as f:
            msg = json.load(f)
            # msg = [m for m in msg if m.get("topic").endswith("/attributes")]
            print(len(msg))
            for m in msg[:2000]:
                send_to_rabbitmq(ch, m, "toGRMS")
