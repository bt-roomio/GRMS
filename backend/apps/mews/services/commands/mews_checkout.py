"""
Django Management Command: Simulate Mews Check-in/Check-out
For testing purposes - simulates Mews WebSocket events
"""

import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from mews.handlers import ReservationEventHandler
from mews.models import MewsConfiguration

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Simulate Mews check-in or check-out event for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-id",
            type=str,
            required=True,
            help="Tenant ID to simulate event for",
        )
        parser.add_argument(
            "--event-type",
            type=str,
            choices=["checkin", "checkout"],
            required=True,
            help="Type of event to simulate (checkin or checkout)",
        )
        parser.add_argument(
            "--reservation-id",
            type=str,
            help="Reservation ID (UUID). If not provided, will use a test ID",
            default="a07eb4fd-998b-4d4c-8976-b39a00a87bd5",
        )
        parser.add_argument(
            "--resource-id",
            type=str,
            help="Resource/Room ID (UUID) - only needed for check-in",
        )
        parser.add_argument(
            "--room-number",
            type=str,
            help="Room number (for auto-creating room if needed)",
        )

    def handle(self, *args, **options):
        tenant_id = options["tenant_id"]
        event_type = options["event_type"]
        reservation_id = options["reservation_id"]
        resource_id = options.get("resource_id")
        room_number = options.get("room_number")

        # Get Mews configuration
        try:
            config = MewsConfiguration.objects.get(tenant__id=tenant_id, is_active=True)
        except MewsConfiguration.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No active Mews configuration found for tenant ID: {tenant_id}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Simulating {event_type} for tenant: {config.tenant.title}"))

        # Create handler
        handler = ReservationEventHandler(config)

        # Create event based on type
        if event_type == "checkin":
            if not resource_id:
                self.stdout.write(self.style.ERROR("--resource-id is required for check-in simulation"))
                return

            # Create check-in event
            start_utc = timezone.now()
            end_utc = start_utc + timedelta(days=1)

            event = {
                "State": "Started",
                "StartUtc": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "EndUtc": end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "AssignedResourceId": resource_id,
                "Type": "Reservation",
                "Id": reservation_id,
            }

            self.stdout.write(
                self.style.WARNING(
                    f"\nℹ️  Note: This will call Mews API to get resource and customer info.\n"
                    f"   Resource ID: {resource_id}\n"
                    f"   Make sure this resource exists in Mews!\n"
                )
            )

        else:  # checkout
            # Create check-out event
            event = {
                "State": "Processed",
                "Type": "Reservation",
                "Id": reservation_id,
            }

        # Display event details
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'='*60}\n"
                f"Simulating Event\n"
                f"{'='*60}\n"
                f"Event Type: {event_type}\n"
                f"Reservation ID: {reservation_id}\n"
                f"Event Data:\n"
            )
        )

        for key, value in event.items():
            self.stdout.write(f"  {key}: {value}")

        self.stdout.write(f"{'='*60}\n")

        # Process event
        try:
            handler.handle_event(event)
            self.stdout.write(self.style.SUCCESS(f"\n✅ {event_type.capitalize()} simulation completed successfully!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Simulation failed: {e}"))
            logger.error(f"Error simulating {event_type}: {e}", exc_info=True)
