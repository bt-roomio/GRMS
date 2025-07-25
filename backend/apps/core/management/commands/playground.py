from django.core.management.base import BaseCommand

from shuttle.models import RPCMessage


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
