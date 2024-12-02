from django.conf import settings
from django.core.management.base import BaseCommand

from main.utils.listening_mq import MQListener

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT

rabbit_queues = {"toGRMSqueueName": "toGRMS", "fromGRMSqueueName": "fromGRMS"}


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def handle(self, *args, **options):
        td = MQListener()
        td.start()
