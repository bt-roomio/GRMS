import json
import random

import redis
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Prefetch

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from main.models import Device
from shuttle.models import Relation

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)


class Command(BaseCommand):
    help = "simulate_message_to_rabbitmq"

    def add_arguments(self, parser):
        parser.add_argument(
            "--value",
            type=int,
            help="value",
            default=1,
        )

    def handle(self, **kwargs):
        tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
        for _ in range(10):
            self.send_messages_connect_disconnect(tenant_id)
        print("Messages sent to RabbitMQ successfully.")

    def device_connectivity_simulation(self, msg):
        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, msg, "/attributes")

    @staticmethod
    def bulk_publish():
        with open("output_500.json", "r") as f:
            data = json.load(f)

        ch = connect_to_rabbitmq()
        for msg in data:
            topic = msg.get("topic")
            if topic.endswith("/telemetry"):
                topic = "/telemetry"
            elif topic.endswith("/attributes"):
                topic = "/attributes"
            send_to_rabbitmq(ch, msg, topic)

    def generate_msg_attributes(self, tenant_id):
        print("Hello")
        devices = self.get_devices(tenant_id)

        for d in devices:
            print(d, d.relations)
            if not d.relations:
                continue

            msg = {
                "sourceDeviceUUID": str(d.relations[0].from_id_id),
                "data": {d.name: {"online": True}},
                "topic": "v1/devices/connect",
            }
            print(f"Generated message for device {d.name}: {str(msg)[:10]}")
            yield msg

    def generate_msg_device_activity(self, tenant_id):
        devices = self.get_devices(tenant_id)

        for d in devices:
            if not d.relations:
                continue

            conn, disc = "v1/gateway/connect", "v1/gateway/disconnect"
            rndm = random.choice([conn, disc])
            msg = {
                "sourceDeviceUUID": str(d.relations[0].from_id_id),
                "data": {"device": d.name},
                "topic": rndm,
            }
            yield msg

    def send_messages_connect_disconnect(self, tenant_id):
        ch = connect_to_rabbitmq()
        for msg in self.generate_msg_device_activity(tenant_id):
            send_to_rabbitmq(ch, msg, "/attributes")

    @staticmethod
    def get_devices(tenant_id=None) -> list[Device]:
        devices = Device.objects.prefetch_related(
            Prefetch("to_relations", queryset=Relation.objects.select_related("from_id").all(), to_attr="relations")
        )
        devices = devices.filter(tenant_id=tenant_id) if tenant_id else devices
        return list(devices)
