from django.core.management.base import BaseCommand
from django.db.models import OuterRef, Subquery

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.get_time import get_mil_sec
from main.models import Room, Device
from main.utils.save_ts_kv import save_telemetry_kv
from shuttle.models import TsKvLatest, RPCMessage
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        # rpc = RPCMessage.objects.last()
        # if not rpc:
        #     self.stdout.write(self.style.ERROR("No RPCMessage found"))
        #     return
        #
        # rpc.additional_info = {"success": True}
        # rpc.received = True
        # rpc.save()
        #
        # self.stdout.write(self.style.SUCCESS(f"Simulated success response for RPCMessage ID: {rpc.id}"))



        message = {"sourceDeviceUUID": "8a94551d-d8ac-44a8-8993-1a609f08e9d7",
                   "data": {"24:3e:b2:da:d3:e3": [{"ts": 1748982055905,
                                                   "values": {
                                                       "rfid_card_event": {
                                                           "access_group": "DENIED",
                                                           "card_uid": "A8 B3 U4 E4",
                                                           "event_ts": 1746561660}}},
                                                  {"ts": 1748982055953,
                                                   "values": {
                                                       "rfid_card_event": {
                                                           "access_group": "MASTER_CARD",
                                                           "card_uid": "8B 02 46 81",
                                                           "event_ts": 1748980860}}},
                                                  {"ts": 1748982056005,
                                                   "values": {
                                                       "rfid_card_event": {
                                                           "access_group": "GUEST",
                                                           "card_uid": "8B 12 46 81",
                                                           "event_ts": 1748980860}}}]},
                   "topic": "v1/gateway/telemetry"}
        # device = Device.objects.get(id="8a94551d-d8ac-44a8-8993-1a609f08e9d7")
        # save_telemetry_kv(device, message.get("data"), get_mil_sec())
        channel = connect_to_rabbitmq()
        send_to_rabbitmq(channel, message, "toGRMS")
