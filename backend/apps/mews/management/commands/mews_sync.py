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

from services.models import Integration
from services.utils.const import MEWS

logger = logging.getLogger(__name__)


class MewsConfigAdapter:
    def __init__(self, integration: Integration):
        additional_info = integration.additional_info or {}
        self.tenant = integration.tenant
        self.client_token = integration.integrator.client_id
        self.access_token = integration.access_token or ""
        self.company_id = integration.hotel_id or ""
        self.environment = additional_info.get("environment", "demo")
        self.last_sync = None

    @property
    def api_base_url(self):
        """Get API base URL based on environment"""
        return {
            "demo": "https://api.mews-demo.com/api/connector/v1",
            "production": "https://api.mews.com/api/connector/v1",
        }.get(self.environment, "https://api.mews.com/api/connector/v1")

    @property
    def ws_url(self):
        """Get WebSocket URL based on environment"""
        return {
            "demo": "wss://ws.mews-demo.com/ws/connector",
            "production": "wss://ws.mews.com/ws/connector",
        }.get(self.environment, "wss://ws.mews.com/ws/connector")


class Command(BaseCommand):
    help = "Sync reservations from Mews for all active configurations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--start-date",
            type=str,
            help="Start date for sync in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). Overrides last_sync.",
        )
        parser.add_argument(
            "--tenant",
            type=str,
            help="Specific tenant title to sync (optional, syncs all if not provided)",
        )

    def handle(self, *args, **options):
        start_date_override = options.get("start_date")
        tenant_filter = options.get("tenant")

        active_integrations = Integration.objects.filter(
            integrator__name__iexact=MEWS,
            integrator__client_id__isnull=False,
            enable=True,
            is_active=True,
        ).select_related("tenant")

        if tenant_filter:
            active_integrations = active_integrations.filter(tenant__title__icontains=tenant_filter)

        if not active_integrations:
            self.stdout.write(self.style.WARNING("No active Mews configurations found"))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {len(active_integrations)} configuration(s) to sync"))

        for integration in active_integrations:
            tenant = integration.tenant
            self.stdout.write(self.style.SUCCESS(f"\n{'=' * 60}"))
            self.stdout.write(self.style.SUCCESS(f"Syncing tenant: {tenant.title}"))
            self.stdout.write(self.style.SUCCESS(f"{'=' * 60}"))

            try:
                config_adapter = MewsConfigAdapter(integration)
                additional_info = integration.additional_info or {}

                # Determine sync period
                if start_date_override:
                    # Use provided start date
                    try:
                        # Try parsing with time first
                        if "T" in start_date_override or " " in start_date_override:
                            start_date = datetime.datetime.fromisoformat(start_date_override.replace("Z", "+00:00"))
                        else:
                            # Parse date only, set to start of day
                            start_date = datetime.datetime.strptime(start_date_override, "%Y-%m-%d")
                            start_date = timezone.make_aware(start_date)
                        self.stdout.write(f"Using custom start date: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    except ValueError:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Invalid start date format: {start_date_override}. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"
                            )
                        )
                        continue
                else:
                    last_sync_str = additional_info.get("last_sync")
                    if last_sync_str:
                        # Parse ISO format datetime
                        start_date = datetime.datetime.fromisoformat(last_sync_str.replace("Z", "+00:00"))
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
                handler = ReservationEventHandler(config_adapter)
                stats = handler.sync_reservations(start_utc, end_utc)

                if "error" in stats:
                    self.stdout.write(self.style.ERROR(f"Sync failed: {stats['error']}"))
                    continue

                current_time = datetime.datetime.now(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                additional_info["last_sync"] = current_time
                integration.additional_info = additional_info
                integration.save(update_fields=["additional_info"])

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

                self.stdout.write(self.style.SUCCESS(f"✓ Sync completed for {tenant.title}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Sync failed for {tenant.title}: {e}"))
                logger.error(f"Sync error for tenant {tenant.title}: {e}", exc_info=True)

        self.stdout.write(self.style.SUCCESS(f"\n{'=' * 60}"))
        self.stdout.write(self.style.SUCCESS("All syncs completed"))
