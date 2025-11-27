"""
Django Management Command: Mews Reservation Sync
Manually sync reservations from Mews for a specific time period
"""

import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from mews.handlers import ReservationEventHandler
from mews.models import MewsConfiguration

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync reservations from Mews for a specific time period"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-id",
            type=str,
            required=True,
            help="Tenant ID to sync reservations for",
        )
        parser.add_argument(
            "--start-date",
            type=str,
            help="Start date in YYYY-MM-DD format (default: today)",
        )
        parser.add_argument(
            "--end-date",
            type=str,
            help="End date in YYYY-MM-DD format (default: tomorrow)",
        )
        parser.add_argument(
            "--days",
            type=int,
            help="Number of days to sync from start-date (alternative to end-date)",
        )

    def handle(self, *args, **options):
        tenant_id = options["tenant_id"]

        # Get Mews configuration for tenant
        try:
            config = MewsConfiguration.objects.get(tenant__id=tenant_id, is_active=True)
        except MewsConfiguration.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No active Mews configuration found for tenant ID: {tenant_id}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Starting sync for tenant: {config.tenant.title}"))

        # Parse dates
        if options.get("start_date"):
            start_date = datetime.strptime(options["start_date"], "%Y-%m-%d")
        else:
            start_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if options.get("end_date"):
            end_date = datetime.strptime(options["end_date"], "%Y-%m-%d")
        elif options.get("days"):
            end_date = start_date + timedelta(days=options["days"])
        else:
            end_date = start_date + timedelta(days=1)

        # Convert to ISO 8601 UTC format
        start_utc = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_utc = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        self.stdout.write(self.style.SUCCESS(f"Syncing reservations from {start_utc} to {end_utc}"))

        # Create handler and sync
        handler = ReservationEventHandler(config)

        try:
            stats = handler.sync_reservations(start_utc, end_utc)

            if "error" in stats:
                self.stdout.write(self.style.ERROR(f"Sync failed: {stats['error']}"))
                return

            # Display results
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{'='*60}\n"
                    f"Sync Results\n"
                    f"{'='*60}\n"
                    f"Total reservations: {stats['total']}\n"
                    f"Checked in: {stats['checked_in']}\n"
                    f"Checked out: {stats['checked_out']}\n"
                    f"Skipped: {stats['skipped']}\n"
                    f"Errors: {stats['errors']}\n"
                    f"{'='*60}\n"
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Sync failed: {e}"))
            logger.error(f"Sync error: {e}", exc_info=True)
