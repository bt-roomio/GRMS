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
        # ch = connect_to_rabbitmq()
        # tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
        # redis_client.delete("temp_test")

        self.device_connectivity_simulation()
        # for _ in range(10):
        #     self.bulk_publish()
        #     for msg in self.generate_msg_attributes(tenant_id):
        #         send_to_rabbitmq(ch, msg, routing_key="/attributes")
        # # Single message publish simulation
        # msg = {
        #     "sourceDeviceUUID": "5aab4f30-3e46-4ae5-9200-0ec6f51aa344",
        #     "data": {
        #         "4c:71:43:10:02:80": [
        #             {"ts": 1766094037000, "values": {"Main Door": 1}},
        #             {"ts": 1749978215720, "values": {"Wardrobe Light": 0}},
        #             {"ts": 1749978215720, "values": {"Room Downlights": 127}},
        #             {"ts": 1749978215720, "values": {"Room Downlights": 1}},
        #         ]
        #     },
        #     "topic": "v1/gateway/telemetry",
        # }
        # msg = {
        #     "sourceDeviceUUID": "5aab4f30-3e46-4ae5-9200-0ec6f51aa344",
        #     "data": {
        #         "4c:71:43:10:02:80": {
        #             "test": time.time(),
        #             "macAddress": "4c:71:43:10:02:80",
        #         }
        #     },
        #     "topic": "v1/gateway/attributes",
        # }
        # for _ in range(10_000):
        #     send_to_rabbitmq(ch, msg, "/attributes")

    def device_connectivity_simulation(self):
        ch = connect_to_rabbitmq()
        gateway = "5aab4f30-3e46-4ae5-9200-0ec6f51aa344"
        sub_dev = "4c:71:43:10:02:80"
        msg = {
            "sourceDeviceUUID": "5aab4f30-3e46-4ae5-9200-0ec6f51aa344",
            # "data": {"gateway_online": True},
            # "topic": "v1/devices/me/attributes",
            "data": {"device": "4c:71:43:10:02:80", "type": "default"},
            "topic": "v1/gateway/disconnect",
        }
        msg = {
            "sourceDeviceUUID": "5aab4f30-3e46-4ae5-9200-0ec6f51aa344",
            "data": {"device": "4c:71:43:10:02:80"},
            "topic": "v1/gateway/disconnect",
        }
        msg1 = {
            "sourceDeviceUUID": "5aab4f30-3e46-4ae5-9200-0ec6f51aa344",
            "data": {
                "keys": "roomNumber,Check-out date,online,mur",
                "device": "4c:71:43:10:02:80",
                "client": False,
                "id": 50860,
            },
            "topic": "v1/gateway/attributes/request",
        }
        msg2 = {
            "sourceDeviceUUID": gateway,
            "data": {
                "ts": 1766582336110,
                "values": {
                    "Fanvil_LOGS": "2025-12-24 18:18:56,110 - |INFO|<Fanvil access logs thread> [FDMCSClient.py] - FDMCSClient get_egs_logs - 72 - FDMCS egsLog fetched: current=1 size=100 total=3256 pages=33 records=100"
                },
            },
            "topic": "v1/devices/me/telemetry",
        }
        send_to_rabbitmq(ch, msg, "/telemetry")

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
        devices = self.get_devices(tenant_id)

        for d in devices:
            # is_gateway = isinstance(d.additional_info, dict) and d.additional_info.get("gateway")
            if not d.relations:  # pyright: ignore
                continue

            msg = {
                "sourceDeviceUUID": str(d.relations[0].from_id_id),  # pyright: ignore
                "data": {d.name: {"online": True}},
                "topic": "/attributes",
            }
            yield msg

    def generate_msg_device_activity(self, tenant_id):
        devices = self.get_devices(tenant_id)

        for d in devices:
            # is_gateway = isinstance(d.additional_info, dict) and d.additional_info.get("gateway")
            if not d.relations:  # pyright: ignore
                continue

            rndm = random.choice(["v1/gateway/connect", "v1/gateway/disconnect"])
            msg = {
                "sourceDeviceUUID": str(d.relations[0].from_id_id),  # pyright: ignore
                "data": {"device": d.name},
                "topic": rndm,
            }
            yield msg

    def send_messages_connect_disconnect(self, tenant_id):
        ch = connect_to_rabbitmq()
        for msg in self.generate_msg_device_activity(tenant_id):
            send_to_rabbitmq(ch, msg, "toGRMS")

    def get_devices(self, tenant_id) -> list[Device]:
        devices = Device.objects.prefetch_related(
            Prefetch("to_relations", queryset=Relation.objects.select_related("from_id").all(), to_attr="relations")
        ).filter(tenant_id=tenant_id)
        return list(devices)
