"""
Django Management Command: Mews Resource Access Tokens (Key Cards)
Fetch and assign resource access tokens (key cards) for active guests to room devices

Documentation: https://mews-systems.gitbook.io/connector-api/operations/resourceaccesstokens#get-all-resource-access-tokens
API Endpoint: https://api.mews-demo.com/api/connector/v1/resourceAccessTokens/getAll

Workflow:
1. Find all active check-ins for tenant's (Guest.is_active=True and Guest.additional_info.mews_reservation_id exists)
2. If check-in exists, fetch resource access tokens for the guest's reservation (body parameter: ServiceOrderIds list of reservation IDs, ActivityStates=['Active']) then filter by Type='RfidTag'
3. After fetching, group key cards by room and assign them to room devices via access_cards_via_card_numbers
4. Save last fetch timestamp from last high UpdatedUtc to Tenant.additional_info['integration_settings']['mews']['last_keycard_fetch']
5. On next run, only fetch key cards updated after last fetch timestamp (parameter: UpdatedUtc)

This command should run every minute for incremental updates.
"""

import datetime
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone
from mews.client import MewsAPIClient

from main.models import Guest, Tenant
from shuttle.utils.access_cards import access_cards_via_card_numbers

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
    help = "Fetch and assign RFID key cards for active guests to room devices (run every minute)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            type=str,
            help="Specific tenant title to process (optional, processes all if not provided)",
        )
        parser.add_argument(
            "--force-full",
            action="store_true",
            help="Force full fetch instead of incremental (ignores last_keycard_fetch)",
        )

    def handle(self, *args, **options):
        tenant_filter = options.get("tenant")
        force_full = options.get("force_full", False)

        # Get all tenants with active Mews integration
        tenants = Tenant.objects.filter(additional_info__integration_settings__mews__enable=True)

        # Find by title from options
        if tenant_filter:
            tenants = tenants.filter(title__icontains=tenant_filter)

        active_tenants = []

        for tenant in tenants:
            if not tenant.additional_info:
                continue

            integration_settings = tenant.additional_info.get("integration_settings", {})
            mews_settings = integration_settings.get("mews", {})
            if mews_settings.get("client_token") and mews_settings.get("access_token"):
                active_tenants.append(tenant)

        if not active_tenants:
            logger.warning("No active Mews configurations found")
            return

        logger.info(f"Processing {len(active_tenants)} tenant(s)")

        # Process each tenant
        total_published = 0
        for tenant in active_tenants:
            logger.debug(f"\n{'='*60}")
            logger.debug(f"Tenant: {tenant.title}")
            logger.debug(f"{'='*60}")

            try:
                # Step 1: Find active guests with Mews reservation IDs
                active_guests = Guest.objects.filter(
                    tenant=tenant,
                    is_active=True,
                    additional_info__mews_reservation_id__isnull=False,
                )
                reservation_ids = list(active_guests.values_list("additional_info__mews_reservation_id", flat=True))

                if not active_guests.exists():
                    logger.warning(f"No active guests with Mews reservations for this {tenant} tenant")
                    continue

                # Step 2: Setup API client
                mews_settings = tenant.additional_info["integration_settings"]["mews"]
                config_adapter = MewsConfigAdapter(tenant, mews_settings)

                api_client = MewsAPIClient(
                    client_token=config_adapter.client_token,
                    access_token=config_adapter.access_token,
                    base_url=config_adapter.api_base_url,
                )

                # Step 3: Determine time range for incremental fetch
                now = timezone.now()
                last_fetch = None

                if not force_full:
                    last_fetch_str = mews_settings.get("last_keycard_fetch")
                    if last_fetch_str:
                        try:
                            # Parse ISO 8601 string
                            last_fetch = datetime.datetime.fromisoformat(last_fetch_str.replace("Z", "+00:00"))
                            logger.info(f"  Last fetch: {last_fetch_str}")
                        except (ValueError, AttributeError) as e:
                            logger.warning(f"Failed to parse last_keycard_fetch: {e}")
                            last_fetch = None

                # If no last fetch, use current time minus 1 days as default
                if last_fetch is None:
                    last_fetch = now - datetime.timedelta(days=1)
                    logger.debug("First fetch - using 1 day ago")

                # Step 4: Fetch access tokens
                start_utc = last_fetch.strftime("%Y-%m-%dT%H:%M:%SZ")
                end_utc = now.strftime("%Y-%m-%dT%H:%M:%SZ")

                logger.debug(f"Fetching tokens updated from {start_utc} to {end_utc}")

                # Fetch with UpdatedUtc filter for incremental updates
                response = api_client.get_resource_access_tokens(
                    service_order_ids=reservation_ids,
                    updated_utc={"StartUtc": "2025-12-10T14:00:00Z", "EndUtc": "2025-12-15T14:00:00Z"},
                    # TODO: change filter updated_utc to use start_utc and end_utc above
                    activity_states=["Active"],
                    limit=100,
                )

                all_tokens = response.get("ResourceAccessTokens", [])
                cursor = response.get("Cursor")

                # Handle pagination
                while cursor:
                    logger.debug("  Fetching next page...")
                    response = api_client.get_resource_access_tokens(
                        service_order_ids=reservation_ids,
                        updated_utc={"StartUtc": start_utc, "EndUtc": end_utc},
                        activity_states=["Active"],
                        cursor=cursor,
                        limit=100,
                    )
                    all_tokens.extend(response.get("ResourceAccessTokens", []))
                    cursor = response.get("Cursor")

                # Step 5: Filter by Type='RfidTag'
                rfid_tokens = [token for token in all_tokens if token.get("Type") == "RfidTag"]

                logger.debug(f"  Found {len(all_tokens)} total token(s), {len(rfid_tokens)} RFID tag(s)")

                if not rfid_tokens:
                    logger.debug("No RFID tags to publish")
                    # Still update last fetch timestamp
                    self._update_last_fetch(tenant, now)
                    continue

                # Step 6: Assign keycards to devices
                self._assign_keycards(tenant, rfid_tokens, active_guests)

                # Step 7: Update last fetch timestamp
                self._update_last_fetch(tenant, now)

                # Display sample data
                if rfid_tokens:
                    logger.debug("\n  Sample key card data:")
                    for idx, token in enumerate(rfid_tokens[:3], 1):
                        logger.debug(f"    {idx}. ID: {token.get('Id', 'N/A')[:20]}...")
                        logger.debug(f"       Value: {token.get('Value', 'N/A')}")
                        logger.debug(
                            f"Valid: {token.get('ValidityStartUtc', 'N/A')} → {token.get('ValidityEndUtc', 'N/A')}"
                        )
                        logger.debug(f"       Reservation: {token.get('ServiceOrderId', 'N/A')[:20]}...")

            except Exception as e:
                logger.exception(f"Error processing tenant {tenant.title}")
                logger.warning(self.style.ERROR(f"  ✗ Failed: {str(e)}"))
                continue

        logger.info(f"\n{'='*60}")
        logger.info(f"Completed. Total key cards assigned: {total_published}")

    def _assign_keycards(self, tenant: Tenant, rfid_tokens: list, active_guests) -> int:
        """
        Assign RFID key cards to room devices via access_cards_via_card_numbers

        Args:
            tenant: Tenant instance
            rfid_tokens: List of RFID token dictionaries
            active_guests: QuerySet of active Guest instances

        Returns:
            Number of assigned cards
        """
        assigned_count = 0

        try:
            # Step 1: Create mapping of reservation_id -> guest
            reservation_to_guest = {}
            for guest in active_guests:
                mews_reservation_id = guest.additional_info.get("mews_reservation_id")
                if mews_reservation_id:
                    if mews_reservation_id not in reservation_to_guest:
                        reservation_to_guest[mews_reservation_id] = []
                    reservation_to_guest[mews_reservation_id].append(guest)

            # Step 2: Group tokens by room
            room_data = {}  # room -> {"guests": set, "cards": set}

            for token in rfid_tokens:
                service_order_id = token.get("ServiceOrderId")
                card_value = token.get("Value")

                if not service_order_id or not card_value:
                    continue

                # Find guests for this reservation
                guests_for_reservation = reservation_to_guest.get(service_order_id, [])

                for guest in guests_for_reservation:
                    if not guest.room:
                        logger.warning(f"Guest {guest.id} has no room assigned")
                        continue

                    room = guest.room

                    # Initialize room data if not exists
                    if room.id not in room_data:
                        room_data[room.id] = {"room": room, "guests": set(), "cards": set()}

                    room_data[room.id]["guests"].add(guest)
                    room_data[room.id]["cards"].add(card_value)

            # Step 3: Call access_cards_via_card_numbers for each room
            for _, data in room_data.items():
                room = data["room"]
                guests = list(data["guests"])
                cards = list(data["cards"])

                try:
                    access_cards_via_card_numbers(guests, room, cards, access=1)
                    assigned_count += len(cards)

                    logger.info(f"Assigned {len(cards)} card(s) for {len(guests)} guest(s) in room {room.number}")

                except Exception as e:
                    logger.exception(f"Failed to assign cards for room {room.number}: {e}")
                    continue

        except Exception as _:
            logger.exception(f"Failed to assign keycards for tenant {tenant.title}")
            raise

        return assigned_count

    def _update_last_fetch(self, tenant: Tenant, fetch_time: datetime.datetime) -> None:
        """
        Update last keycard fetch timestamp in tenant.additional_info

        Args:
            tenant: Tenant instance
            fetch_time: Timestamp of this fetch operation
        """
        try:
            # Ensure additional_info structure exists
            if not tenant.additional_info:
                tenant.additional_info = {}

            if "integration_settings" not in tenant.additional_info:
                tenant.additional_info["integration_settings"] = {}

            if "mews" not in tenant.additional_info["integration_settings"]:
                tenant.additional_info["integration_settings"]["mews"] = {}

            # Update last_keycard_fetch as ISO 8601 string
            tenant.additional_info["integration_settings"]["mews"]["last_keycard_fetch"] = fetch_time.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            tenant.save(update_fields=["additional_info"])

            logger.info(f"Updated last_keycard_fetch for tenant {tenant.title}")

        except Exception as _:
            logger.exception(f"Failed to update last_keycard_fetch for tenant {tenant.title}")
            # Don't raise - this shouldn't fail the entire operation
