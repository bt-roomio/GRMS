from django.core.management.base import BaseCommand
from shuttle.models import RPCMessage


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        rpc = RPCMessage.objects.last()
        if not rpc:
            self.stdout.write(self.style.ERROR("No RPCMessage found"))
            return

        rpc.additional_info = {"success": True}
        rpc.received = True
        rpc.save()

        self.stdout.write(self.style.SUCCESS(f"Simulated success response for RPCMessage ID: {rpc.id}"))
