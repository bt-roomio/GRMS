from django.core.management.base import BaseCommand

from shuttle.models import RPCMessage


class Command(BaseCommand):
    help = "Mark the last 5 RPC messages as received with success=True"

    def handle(self, **_):
        for msg in RPCMessage.objects.order_by("-created_at")[:5]:
            msg.received = True
            msg.additional_info = {**(msg.additional_info or {}), "success": True}
            msg.save(update_fields=["received", "additional_info"])
            self.stdout.write(f"{msg.id}: {msg.additional_info}")
