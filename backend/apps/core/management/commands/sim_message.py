import json
import random
import time

import redis
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from core.management.mq.fias import handle_fias
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

    def handle(self, **_):
        nines_gateway_id = "48aedc23-1f2f-49ba-ab36-20ba650af5c7"

        msg1 = self.single_telemetry(nines_gateway_id, "0c:2e:e4:6a:f6:45")
        msg2 = self.single_telemetry(nines_gateway_id, "08:b0:bb:1f:a2:37")
        msg3 = self.single_telemetry(nines_gateway_id, "18:a0:6e:41:02:80")
        self.send_msg(msg1, "/telemetry")
        self.send_msg(msg2, "/telemetry")
        self.send_msg(msg3, "/telemetry")
        # for msg in self.generate_msg_telemetry(tenant_id):
        #     self.send_msg(msg, "/telemetry")

        # for msg in self.generate_msg_attributes(tenant_id):
        #     self.send_msg(msg, "/attributes")

    def send_msg(self, msg, routing_key):
        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, msg, routing_key)

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
            if not d.relations:
                continue

            msg = {
                "sourceDeviceUUID": str(d.relations[0].from_id_id),
                "data": {"gatewayOnline": random.choice([True, False])},
                "topic": "v1/devices/me/attributes",
            }
            print(f"Generated message for device {msg['sourceDeviceUUID']}: {str(msg)[:10]}")
            yield msg

    def generate_msg_telemetry(self, tenant_id):
        devices = self.get_devices(tenant_id)

        for d in devices:
            if not d.relations:
                continue

            msg = self.single_telemetry(str(d.relations[0].from_id_id), d.name)
            print(f"Generated message for device {msg['sourceDeviceUUID']}: {str(msg)[:10]}")
            yield msg

    def fias_message(self, *args, **options):
        data = {
            "command": "checkin",
            "roomName": "153",
            "reservationNumber": "4001",
            "shareFlag": False,
            "messageDate": 1773231216000,
            "checkInDate": 1773180000000,
            "checkOutDate": 1773266400000,
            "guestGroupNumber": None,
            "guestTitle": None,
            "guestFirstName": None,
            "guestName": " Ytest ",
            "language": "English / American",
            "workstationId": "THEOVASQL",
            "swapFlag": 0,
        }
        data = {
            "command": "keydelete",
            "operationId": "keyread|THEOVASQL|MyWorkstation|||260331|113238",
            "requiresRpcConfirmation": True,
            "keyCoder": "MyWorkstation",
            "roomName": "215",
            "workstationId": "THEOVASQL",
            "messageDate": 1774945958000,
            "reservationNumber": None,
        }
        data = {
            "command": "keyrequest",
            "keyType": "newKeyRequest",
            "keyCoder": "MyWorkstation",
            "roomName": "215",
            "keyCount": "2",
            "checkInDate": 1777507200000,
            "messageDate": 1777574505000,
            "operationId": "keyrequest|THEOVASQL|1|701|104|260430|184145",
            "checkOutDate": 1773316800000,
            "workstationId": "THEOVASQL",
            "guestGroupNumber": None,
            "reservationNumber": "701",
            "requiresRpcConfirmation": True,
        }

        device = get_object_or_404(Device, pk="7778a61d-eefa-4933-b187-699f2baa3744")
        device = {
            "id": str(device.id),
            "name": device.name,
            "tenant_id": str(device.tenant_id),
            "device_profile_id": str(device.device_profile_id),
        }
        handle_fias(data, device)

    def generate_msg_access_door_log(self):
        d = get_object_or_404(Device, pk="cf193bcc-7801-4d76-8321-0d5c63e54293")
        msg = {
            "sourceDeviceUUID": "5aab4f30-3e46-4ae5-9200-0ec6f51aa344",
            "data": {
                d.name: [
                    {
                        "ts": 1774079212319,
                        "values": {
                            "rfid_card_event": {
                                "access_log_id": "1774079209000",
                                "lock_type": "ttlock",
                                "card_uid": "Pasword unlock",
                                "open_type": "unknown",
                                "openResult": 1,
                                "event_ts": 1774079212319,
                            }
                        },
                    }
                ]
            },
            "topic": "v1/gateway/telemetry",
        }

        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, msg, "/attributes")

        print(f"Generated message for device {d.name}: {str(msg)[:10]}")

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
            Prefetch(
                "to_relations",
                queryset=Relation.objects.select_related("from_id").all(),
                to_attr="relations",
            )
        )
        devices = devices.filter(tenant_id=tenant_id) if tenant_id else devices
        return list(devices)

    def single_telemetry(self, parent_id: str, device_name: str):
        return {
            "sourceDeviceUUID": parent_id,
            "data": {
                f"{device_name}": [
                    {
                        "ts": time.time(),
                        "values": {
                            "Wifi Relay": random.randint(0, 100),
                            # "MUR Relay": random.randint(0, 100),
                            # "Room Temperature": random.randint(0, 100),
                            # "AC ON OFF": random.randint(0, 1),
                            # "Occupancy State": random.randint(0, 1),
                        },
                    }
                ]
            },
            "topic": "v1/gateway/telemetry",
        }
