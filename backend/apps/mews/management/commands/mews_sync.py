"""
Django Management Command: Mews Reservation Sync
Automatically sync reservations from Mews for all active configurations
"""

import datetime
import logging
from datetime import timezone as dt_timezone

from django.core.management.base import BaseCommand
from django.utils import timezone
from mews.handlers import ReservationEventHandler
from mews.models import MewsConfiguration

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync reservations from Mews for all active configurations"

    def handle(self, *args, **options):
        # Get active Mews configurations with auto_sync enabled
        configs = MewsConfiguration.objects.filter(is_active=True, auto_sync=True)

        if not configs.exists():
            self.stdout.write(self.style.WARNING("No active Mews configurations found with auto_sync enabled"))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {configs.count()} configuration(s) to sync"))

        # Process each configuration
        for config in configs:
            self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
            self.stdout.write(self.style.SUCCESS(f"Syncing tenant: {config.tenant.title}"))
            self.stdout.write(self.style.SUCCESS(f"{'='*60}"))

            try:
                # Determine sync period
                if config.last_sync:
                    # Sync from last_sync to now
                    start_date = config.last_sync
                    self.stdout.write(f"Last sync: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    # First sync: today 00:00:00 to tomorrow 00:00:00
                    start_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    self.stdout.write("First sync - using today's date")

                # End date is now
                end_date = timezone.now()

                # Convert to ISO 8601 UTC format
                start_utc = start_date.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                end_utc = end_date.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                self.stdout.write(f"Syncing from {start_utc} to {end_utc}")

                # Create handler and sync
                handler = ReservationEventHandler(config)
                stats = handler.sync_reservations(start_utc, end_utc)

                if "error" in stats:
                    self.stdout.write(self.style.ERROR(f"Sync failed: {stats['error']}"))
                    continue

                # Update last_sync timestamp
                config.last_sync = datetime.datetime(2025, 12, 4, 0, 0, 0, tzinfo=dt_timezone.utc)
                config.save(update_fields=["last_sync"])

                # Display results
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nSync Results:\n"
                        f"  Total reservations: {stats['total']}\n"
                        f"  Checked in: {stats['checked_in']}\n"
                        f"  Checked out: {stats['checked_out']}\n"
                        f"  Skipped: {stats['skipped']}\n"
                        f"  Errors: {stats['errors']}\n"
                    )
                )

                self.stdout.write(self.style.SUCCESS(f"✓ Sync completed for {config.tenant.title}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Sync failed for {config.tenant.title}: {e}"))
                logger.error(f"Sync error for tenant {config.tenant.title}: {e}", exc_info=True)

        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS("All syncs completed"))
