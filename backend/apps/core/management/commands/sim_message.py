import json
import time

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
        # value = kwargs["value"]
        # self.bulk_publish()
        # return
        # msg = {"sourceDeviceUUID": "e00ea2b8-d11a-489c-adcb-8ed31938fd25",
        #        "data": {
        #            "00:e4:b2:da:d3:e4": [
        #                {
        #                    "ts": 1763550823323,
        #                    "values": {
        #                        "rfid_card_event": {
        #                            "access_group": "GUEST",
        #                            "card_uid": "8B 02 46 80",
        #                            "event_ts": 1748980860,
        #                        }
        #                    }
        #                }
        #            ]
        #        }, "topic": "v1/gateway/telemetry"}
        msg = {"sourceDeviceUUID": "e00ea2b8-d11a-489c-adcb-8ed31938fd25",
            "data": {
                "00:e4:b2:da:d3:e4": [
                    {"ts": 1763550823323,
                        "values": {
                            "rfid_card_event": {
                                    "fanvil_access_log_id": "1992095148185051139",
                                    "card_uid": "",
                                    "open_type": "Remote",
                                    "openResult": True,
                                    "event_ts": 1763281405,
                                    "displayName": "Amarande Barrier Exit"
                                }
                            }
                        }]}, "topic": "v1/gateway/telemetry"
            }
        ch = connect_to_rabbitmq()
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
