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
        # tenant_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
        # for _ in range(100):
        #     self.send_messages_connect_disconnect("28c81921-f78e-4864-87d2-cec674f19d1c")

        # msg = {
        #     "sourceDeviceUUID": "99dc4d17-e874-4a1f-9029-7e2710872c1b",
        #     "data": {"c8:f8:07:1d:18:78": [{"online": True}]},
        #     "topic": "v1/gateway/attributes",
        # }
        msg = {
            "sourceDeviceUUID": "5aab4f30-3e46-4ae5-9200-0ec6f51aa344",
            "data": {
                "4c:71:43:10:02:80": [
                    {
                        "ts": 1749978217548,
                        "values": {
                            "messageFromFIAS": {
                                "command": "checkin",
                                "language": "English / American",
                                "roomName": "106",
                                "swapFlag": 1,  # WARN: can't be blank or null
                                "guestName": "Test 1",
                                "shareFlag": False,
                                "guestTitle": None,
                                "checkInDate": 1766523600000,
                                "messageDate": 1766785828000,
                                "checkOutDate": 1766610000000,
                                "workstationId": None,
                                "guestFirstName": "Test",  # WARN: can't be blank or null
                                "guestGroupNumber": "45775",
                                "reservationNumber": "4564701",
                            },
                        },
                    },
                ]
            },
            "topic": "v1/gateway/telemetry",
        }
        if kwargs["value"] == 2:
            msg["data"]["4c:71:43:10:02:80"][0]["values"]["messageFromFIAS"] = {
                "command": "checkout",
                "roomName": "106",
                "swapFlag": 1,
                "shareFlag": False,
                "messageDate": 1766577088000,
                "workstationId": None,
                "reservationNumber": "4564701",
            }

        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, msg, "/telemetry")

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
        ch = connect_to_rabbitmq()
        for msg in self.generate_messages(tenant_id):
            send_to_rabbitmq(ch, msg, "toGRMS")
