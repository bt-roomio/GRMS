from uuid import UUID

from django.core.management.base import BaseCommand

from main.models import Device
from shuttle.models import RPCMessage, TsKvDictionary, TsKvLatest


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        device_id = UUID("04966159-619f-4b07-a7a9-bb0eeaf642f8")  # replace with your actual device UUID
        key_name = "MUR Relay"  # or "MUR Relay", "Occupancy State"
        value = 1  # 1 to turn ON, 0 to turn OFF

        key_dict = TsKvDictionary.objects.filter(key=key_name).first()
        if not key_dict:
            print(f"Key '{key_name}' not found in TsKvDictionary.")
            return

        obj = TsKvLatest.objects.filter(entity_id=device_id, key=key_dict.key_id).first()
        if obj:
            obj.long_v = value
            obj.save()
            print(f"{key_name} updated to {value} for device {device_id}")
        else:
            print(f"No existing entry found for device {device_id} and key '{key_name}'")

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
