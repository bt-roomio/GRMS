import json

from django.core.management.base import BaseCommand

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq


class Command(BaseCommand):
    help = "simulate_message_to_rabbitmq"

    def add_arguments(self, parser):
        parser.add_argument(
            "--value",
            type=str,
            help="Queue name",
            default="v1/devices/me/attributes/request",
        )

    def handle(self, *args, **kwargs):
        val = kwargs["value"]

        msg = {
            "sourceDeviceUUID": "47aef21b-6cc9-4ec5-8573-1a6f491940c0",
            "data": {
                "38:0c:6e:41:02:80": {
                    "macAddress": "04:60:e8:78:d3:e4",
                    "cmd": "getSystemInfo",
                    "dressing_light": val,
                    "systemType": "HCM350V",
                    "hwRevision": "V4.1",
                    "mainBootVersion": 1025,
                    "mainFwVersion": 16896014,
                    "peripheryBootVersion": 4294967295,
                    "peripheryFwVersion": 11,
                    "configFileSiteVersion": 115,
                    "configFileDate": "20241023",
                    "configFileTime": "1501",
                    "configFileCrc32": 2208071169,
                    "bootDefaultsSiteVersion": 0,
                    "bootDefaultsDate": "",
                    "bootDefaultsTime": "",
                    "bootDefaultsCrc32": 0,
                    "siteVersion": 111,
                    "rfidCfgFileCrc32": 0,
                    "ready": "true",
                    "ipAddress": "10.10.214.251",
                }
            },
            "topic": "v1/gateway/attributes",
        }
        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, msg, "toGRMS")
        return

        with open("output_500.json", "r") as f:
            msg = json.load(f)
            attrs = [m for m in msg if m.get("topic").endswith("/attributes")]
            print(len(attrs))
            for m in attrs:
                if m.get("topic").endswith("/telemetry"):
                    send_to_rabbitmq(ch, m, "/telemetry")
                elif m.get("topic").endswith("/attributes"):
                    send_to_rabbitmq(ch, m, "/attributes")
                elif m.get("topic") == "v1/devices/me/attributes/request":
                    send_to_rabbitmq(ch, m, "v1/devices/me/attributes/request")
                elif m.get("topic") == "v1/gateway/attributes/request":
                    send_to_rabbitmq(ch, m, "v1/gateway/attributes/request")
                elif m.get("topic") == "v1/gateway/rpc":
                    send_to_rabbitmq(ch, m, "v1/gateway/rpc")
                else:
                    send_to_rabbitmq(ch, m, "toGRMS")
