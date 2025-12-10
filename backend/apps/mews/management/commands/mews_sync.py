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

from main.models import Tenant

logger = logging.getLogger(__name__)


class MewsConfigAdapter:
    """
    Adapter to provide MewsConfiguration interface using Tenant.additional_info data
    """

    def __init__(self, tenant: Tenant, mews_settings: dict):
        self.tenant = tenant
        self._mews_settings = mews_settings
        self.client_token = mews_settings.get("client_token", "")
        self.access_token = mews_settings.get("access_token", "")
        self.company_id = mews_settings.get("hotel_id", "")
        self.environment = mews_settings.get("environment", "demo")
        self.last_sync = None  # Will be managed separately if needed

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

    def handle(self, *args, **options):
        # Get all tenants with active Mews integration
        tenants = Tenant.objects.filter(additional_info__integration_settings__mews__enable=True)
        active_tenants = []

        for tenant in tenants:
            if not tenant.additional_info:
                continue

            integration_settings = tenant.additional_info.get("integration_settings", {})
            mews_settings = integration_settings.get("mews", {})
            if mews_settings.get("client_token", False) and mews_settings.get("access_token", False):
                active_tenants.append(tenant)

        if not active_tenants:
            self.stdout.write(self.style.WARNING("No active Mews configurations found"))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {len(active_tenants)} configuration(s) to sync"))

        # Process each tenant
        for tenant in active_tenants:
            self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
            self.stdout.write(self.style.SUCCESS(f"Syncing tenant: {tenant.title}"))
            self.stdout.write(self.style.SUCCESS(f"{'='*60}"))

            try:
                mews_settings = tenant.additional_info["integration_settings"]["mews"]

                # Create config adapter
                config_adapter = MewsConfigAdapter(tenant, mews_settings)

                # Determine sync period
                # Get last_sync from tenant's additional_info if stored there
                last_sync_str = mews_settings.get("last_sync")
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

                # Update last_sync timestamp in tenant's additional_info
                current_time = datetime.datetime.now(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                mews_settings["last_sync"] = current_time
                tenant.additional_info["integration_settings"]["mews"] = mews_settings
                tenant.save(update_fields=["additional_info"])

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

        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS("All syncs completed"))
