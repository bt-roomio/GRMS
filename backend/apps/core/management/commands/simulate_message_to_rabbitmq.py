from django.core.management.base import BaseCommand

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.get_time import get_mil_sec


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        msg = {
            "sourceDeviceUUID": "c6fe44a3-b349-491d-bd7b-31c32dcaf3db",
            "data": {
                "40:76:2E:18:DB:32": [
                    {
                        "ts": 1749978217548,
                        "values": {
                            "Room Temperature": 20,
                            "AC ON OFF": 0,
                            "Setpoint": 1700,
                            "Fan Speed": 0,
                            "Valve cool/heat": 3173,
                            "Fan toggle": 3173,
                            "Dim CH1": 0,
                            "Dim CH2": 0,
                            "Dim CH3": 0,
                            "Dim CH4": 0,
                            "Outdoor Lights": 0,
                            "Cabinet": 0,
                            "Kitchen": 0,
                            "Pendant": 0,
                            "Lounge": 0,
                            "Heating Relay": 0,
                        },
                    }
                ]
            },
            "topic": "v1/gateway/telemetry",
        }
        msg1 = {
            "sourceDeviceUUID": "c6fe44a3-b349-491d-bd7b-31c32dcaf3db",
            "data": [
                {
                    "ts": get_mil_sec(),
                    "values": {
                        "RoomIo_LOGS": "2025-06-16 09:03:35,908 - |WARNING|<Roomio connector socket server thread> [roomio_connector.py] - roomio_connector send_ping - 651 - No ping response from 10.10.214.139 (attempt 1)"
                    },
                }
            ],
            "topic": "v1/devices/me/telemetry",
        }
        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, msg, "/telemetry")

        # with open("output_500.json", "r") as f:
        #     msg = json.load(f)
        #     attrs = [m for m in msg if m.get("topic").endswith("/attributes")]
        #     print(len(attrs))
        #     for m in attrs:
        #         send_to_rabbitmq(ch, m, "/attributes")
        #
        #     msg = [m for m in msg if m.get("topic").endswith("/telemetry")]
        #     print(len(msg))
        #     for m in msg:
        #         send_to_rabbitmq(ch, m, "/telemetry")
