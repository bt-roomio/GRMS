from django.conf import settings
from django.core.management.base import BaseCommand

from main.models import Device
from shuttle.models import TsKv

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        devices = Device.objects.all()
        for device in devices:
            TsKv.objects.create(entity=device, key=45, long_v=23)
