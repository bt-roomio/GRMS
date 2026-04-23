from django.core.management.base import BaseCommand
from mews.handlers import ReservationEventHandler
from mews.management.commands.mews_access_tokens import MewsConfigAdapter

from main.models import Tenant


class Command(BaseCommand):
    help = "Simulate Mews Event"

    def handle(self, **options):
        tenant = Tenant.objects.get(id="f42ca82a-37a9-4e20-97d7-216dae07455f")
        mews_settings = tenant.additional_info["integration_settings"]["mews"]
        config = MewsConfigAdapter(tenant, mews_settings)
        print(options)

        if config:
            handler = ReservationEventHandler(config)
            event = {
                # "State": "Canceled",
                "State": "Confirmed",
                "StartUtc": "2026-04-19T16:00:00Z",
                "EndUtc": "2026-04-25T16:00:00Z",
                # "AssignedResourceId": None,
                "AssignedResourceId": "16b286f7-83d9-4d59-bd37-b32b009f0375",
                "Type": "Reservation",
                "Id": "7bfe3636-8ba6-4423-8481-b42c0064ea22",
            }

            event = {
                "State": "Confirmed",
                "StartUtc": "2026-04-18T16:00:00Z",
                "EndUtc": "2026-04-19T16:00:00Z",
                # "AssignedResourceId": "ea269cda-7d69-4bc6-b964-b32b00b53dfe",  # 220
                "AssignedResourceId": "a0110784-5f52-4047-8efb-b32b00b52b88",  # 219
                "Type": "Reservation",
                "Id": "76c560d9-266b-40ae-b3c8-b42e01354a9f",  # Sophia Ananda
            }
            event = {
                "State": "Confirmed",
                "StartUtc": "2026-04-18T16:00:00Z",
                "EndUtc": "2026-04-20T16:00:00Z",
                "AssignedResourceId": "a0110784-5f52-4047-8efb-b32b00b52b88",
                "Type": "Reservation",
                "Id": "79954173-3fea-434f-b692-b42f004f9446",
            }
            event = {
                "State": "Processed",
                "StartUtc": "2026-04-16T16:00:00Z",
                "EndUtc": "2026-04-17T05:04:18Z",
                "AssignedResourceId": "7d62079f-b234-4446-b651-b32b009f34a5",
                "Type": "Reservation",
                "Id": "9728f4af-f224-47fa-87ac-b42e0131a4d6",
            }
            event = {
                "State": "Started",
                "StartUtc": "2026-04-16T16:00:00Z",
                "EndUtc": "2026-04-17T05:04:18Z",
                "AssignedResourceId": "a0110784-5f52-4047-8efb-b32b00b52b88",  # 219
                "Type": "Reservation",
                "Id": "9728f4af-f224-47fa-87ac-b42e0131a4d6",
            }

            handler.handle_event(event)

            # handler.handle_event(
            #     # {
            #     #     "State": "Confirmed",
            #     #     "StartUtc": "2026-04-14T16:00:00Z",
            #     #     "EndUtc": "2026-04-16T16:00:00Z",
            #     #     "AssignedResourceId": "16b286f7-83d9-4d59-bd37-b32b009f0375",
            #     #     "Type": "Reservation",
            #     #     "Id": "c32e97bd-e5b0-47cc-ab6c-b42c0084698b",
            #     # }
            #     {
            #         "State": "Confirmed",
            #         "StartUtc": "2026-04-15T16:00:00Z",
            #         "EndUtc": "2026-04-17T16:00:00Z",
            #         "AssignedResourceId": "16b286f7-83d9-4d59-bd37-b32b009f0375",
            #         "Type": "Reservation",
            #         "Id": "7bfe3636-8ba6-4423-8481-b42c0064ea22",
            #     }
            #     # {
            #     #     "State": "Canceled",
            #     #     "StartUtc": "2026-04-17T16:00:00Z",
            #     #     "EndUtc": "2026-04-19T16:00:00Z",
            #     #     "AssignedResourceId": None,
            #     #     "Type": "Reservation",
            #     #     "Id": "e943a2c7-ef92-4b08-b354-b42c007ceed6",
            #     # }
            #     # {
            #     #     "State": "Canceled",
            #     #     "StartUtc": "2026-04-08T06:47:49Z",
            #     #     "EndUtc": "2026-04-09T06:47:49Z",
            #     #     "AssignedResourceId": None,
            #     #     "Type": "Reservation",
            #     #     "Id": "cfaf2316-37db-4422-8a80-b2eb00a0f500",
            #     # }
            #     # {
            #     #     "State": "Confirmed",
            #     #     "StartUtc": "2026-04-13T16:00:00Z",
            #     #     "EndUtc": "2026-04-15T16:00:00Z",
            #     #     "AssignedResourceId": "892b0ed7-3354-45a7-823c-abd10133489c",
            #     #     "Type": "Reservation",
            #     #     "Id": "3d14ff7e-013b-439e-a3a8-b42b00f947a1",
            #     # }
            #     # {
            #     #     # "State": "Confirmed",
            #     #     "State": "Started",
            #     #     # "State": "Canceled",
            #     #     "StartUtc": "2026-04-05T17:00:00Z",
            #     #     "EndUtc": "2026-04-15T17:00:00Z",
            #     #     "Type": "Reservation",
            #     #     # "AssignedResourceId": "0b7f611c-f19c-4328-87a2-b2b400806663",
            #     #     "AssignedResourceId": "0e3430a0-35de-48cd-b01a-b40b01052590",
            #     #     "Id": "114c46ae-4203-47a1-82ea-b3a60086e98f",
            #     # }
            #     # {
            #     #     # "State": "Confirmed",
            #     #     "State": "Started",
            #     #     # "State": "Canceled",
            #     #     "StartUtc": "2026-04-05T17:00:00Z",
            #     #     "EndUtc": "2026-04-15T17:00:00Z",
            #     #     "Type": "Reservation",
            #     #     "AssignedResourceId": "0b7f611c-f19c-4328-87a2-b2b400806663",
            #     #     "Id": "9691d006-1025-4f9d-be6f-b41701182037",
            #     # }
            # )
