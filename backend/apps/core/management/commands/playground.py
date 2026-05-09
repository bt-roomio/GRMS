from django.core.management.base import BaseCommand

from shuttle.models import RPCMessage


class Command(BaseCommand):
    help = "Playground"

    def handle(self, **_):
        rpcs = RPCMessage.objects.order_by("-id")[:5]

        if not rpcs:
            self.stdout.write(self.style.ERROR("No RPCMessage found"))
            return

        for rpc in rpcs:
            print(rpc.id)
            rpc.additional_info = {"success": True}
            rpc.received = True
            rpc.save(update_fields=["additional_info", "received"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Simulated success response for last {len(rpcs)} RPCMessage(s): "
                + ", ".join(str(r.id) for r in rpcs)
            )
        )
