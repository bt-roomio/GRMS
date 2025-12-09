import json

from django.core.management.base import BaseCommand

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq


class Command(BaseCommand):
    help = "simulate_message_to_rabbitmq"

    def add_arguments(self, parser):
        parser.add_argument(
            "--value",
            type=int,
            help="value",
            default=1,
        )

    def handle(self, *args, **kwargs):
        msg = {
            "sourceDeviceUUID": "47aef21b-6cc9-4ec5-8573-1a6f491940c0",
            "data": {
                "device": "6c:7f:b2:da:d3:e4",
            },
            "topic": "v1/gateway/connect",
        }
        ch = connect_to_rabbitmq()
        for _ in range(10):
            send_to_rabbitmq(ch, msg, "toGRMS")

    @staticmethod
    def bulk_publish():
        with open("output_500.json", "r") as f:
            data = json.load(f)

        ch = connect_to_rabbitmq()
        for msg in data:
            topic = msg.get("topic")
            if "telemetry" in topic:
                print(msg)
                send_to_rabbitmq(ch, msg, "toGRMS")

    def generate_messages(self, tenant_id):
        import random

        from main.models import Device

        devices = Device.objects.filter(tenant_id=tenant_id)
        count = 0
        for d in devices:
            gateway = d.get_gateway
            if not gateway:
                continue

            msg = {"sourceDeviceUUID": str(gateway.id), "data": {"device": d.name}}
            rr = random.choice(["v1/gateway/connect", "v1/gateway/disconnect"])
            msg["topic"] = rr
            if rr == "v1/gateway/connect":
                msg["data"]["type"] = "default"
            count += 1
            yield msg
        print(f"Total devices: {count}")

    def send_messages_connect_disconnect(self, tenant_id):
        for msg in self.generate_messages(tenant_id):
            ch = connect_to_rabbitmq()
            send_to_rabbitmq(ch, msg, "toGRMS")
