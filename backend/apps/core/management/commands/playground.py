from uuid import UUID

from django.core.management.base import BaseCommand
from django.db.models import F, Func, JSONField, OuterRef, Subquery
from django.db.models.functions import Coalesce

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.get_time import get_mil_sec
from main.models import Room, Device
from main.utils.save_ts_kv import save_telemetry_kv
from shuttle.models import TsKvLatest, RPCMessage, TsKvDictionary
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        rpc_message = RPCMessage.objects.order_by('-created_at')[:5]
        if not rpc_message:
            self.stdout.write(self.style.ERROR("No RPCMessage found"))
            return
        for rpc in rpc_message:
            print(rpc.id)
            rpc.additional_info = {"success": True}
            rpc.received = True
            rpc.save()

        # self.stdout.write(self.style.SUCCESS(f"Simulated success response for RPCMessage ID: {rpc_message.id}"))
