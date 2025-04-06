from pyexpat.errors import messages

from django.core.management.base import BaseCommand
from core.utils.get_time import get_mil_sec
from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from main.models import Device
from core.management.handlers_mq import save_telemetry_kv


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        # message = {'sourceDeviceUUID': '47aef21b-6cc9-4ec5-8573-1a6f491940c0', 'data': {'Oracle PMS main': [
        #     {'ts': 1743491888302, 'values': {
        #         'messageFromFIAS': {'command': 'checkin', 'roomName': '111', 'reservationNumber': '3352102',
        #                             'shareFlag': False, 'messageDate': 1727722890000, 'checkInDate': 1727636400000,
        #                             'checkOutDate': 1728241200000, 'guestGroupNumber': '33978', 'guestTitle': 'Mrs.',
        #                             'guestFirstName': 'Dorte Maarbjerg', 'guestName': 'Stigaard',
        #                             'language': 'English / American', 'workstationId': None}}}]},
        #            'topic': 'v1/gateway/telemetry'}
        message = {'sourceDeviceUUID': '47aef21b-6cc9-4ec5-8573-1a6f491940c0', 'data': {'Oracle PMS main': [
            {'ts': 1743766652192, 'values': {
                'messageFromFIAS': {'command': 'checkout', 'roomName': '111', 'reservationNumber': '3352102',
                                    'shareFlag': False, 'messageDate': 1727738810000, 'workstationId': None}}}]},
                   'topic': 'v1/gateway/telemetry'}
        channel = connect_to_rabbitmq()
        send_to_rabbitmq(channel, message, "toGRMS")
