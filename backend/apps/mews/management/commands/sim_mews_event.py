from django.core.management.base import BaseCommand
from mews.handlers import ReservationEventHandler
from mews.models import MewsConfiguration

from core.utils.query_debugger import query_debugger


class Command(BaseCommand):
    help = "Simulate Mews Event"

    @query_debugger
    def handle(self, *args, **options):
        config = MewsConfiguration.objects.first()
        if config:
            handler = ReservationEventHandler(mews_config=config)
            handler.handle_event(
                {
                    "State": "Started",
                    "StartUtc": "2025-12-01T17:00:00Z",
                    "EndUtc": "2025-12-02T17:00:00Z",
                    "Type": "Reservation",
                    "AssignedResourceId": "0b7f611c-f19c-4328-87a2-b2b400806663",
                    "Id": "114c46ae-4203-47a1-82ea-b3a60086e98f",
                }
            )
