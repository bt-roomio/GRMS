import json

from django.core.management.base import BaseCommand

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq


class Command(BaseCommand):
    help = "simulate_message_to_rabbitmq"

    def handle(self, **_):
        msg = {
            "sourceDeviceUUID": "c6fe44a3-b349-491d-bd7b-31c32dcaf3db",
            "data": {"30:25:46:f5:db:32": {"online": True}},
            "topic": "v1/gateway/attributes",
        }
        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, msg, "/telemetry")

        # with open("output.json", "r") as f:
        #     msg = json.load(f)
        #     # attrs = [m for m in msg if m.get("topic").endswith("/attributes")]
        #     # print(len(attrs))
        #     # for m in attrs:
        #     #     send_to_rabbitmq(ch, m, "/attributes")
        #     #
        #     msg = [m for m in msg if m.get("topic").endswith("/attributes")]
        #     feeding = 1000
        #     print("total, ", len(msg), "feeding", feeding)
        #     msg = msg[:feeding]
        #     for m in msg:
        #         send_to_rabbitmq(ch, m, "/attributes")
