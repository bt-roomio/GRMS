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
from services.models import Integration
from services.utils.const import MEWS
from shuttle.utils.access_cards import access_cards_via_card_numbers

logger = logging.getLogger(__name__)


class MewsConfigAdapter:
    def __init__(self, integration: Integration):
        additional_info = integration.additional_info or {}
        self.tenant = integration.tenant
        self.client_token = integration.integrator.client_id
        self.access_token = integration.access_token or ""
        self.company_id = integration.hotel_id or ""
        self.environment = additional_info.get("environment", "demo")
        self.roomio_access_control = additional_info.get("roomio_access_control", False)

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

    def handle(self, **_):
        active_integrations = Integration.objects.filter(
            integrator__name__iexact=MEWS,
            integrator__client_id__isnull=False,
            enable=True,
            is_active=True,
        ).select_related("tenant")

        if not active_integrations:
            logger.warning("No active Mews configurations found")
            return

        logger.info(f"Processing {len(active_integrations)} tenant(s)")

        total_published = 0
        for integration in active_integrations:
            tenant = integration.tenant
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Tenant: {tenant.title}")
            logger.info(f"{'=' * 60}")

            try:
                # Step 1: Find active guests with Mews reservation IDs
                active_guests = Guest.objects.filter(
                    tenant=tenant,
                    is_active=True,
                    additional_info__mews_reservation_id__isnull=False,
                )
                reservation_ids = list(
                    active_guests.values_list("additional_info__mews_reservation_id", flat=True).distinct()
                )

                if not reservation_ids:
                    logger.warning(f"No active guests with Mews reservations for tenant {tenant}")
                    continue

                # Step 2: Setup API client
                config_adapter = MewsConfigAdapter(integration)

                api_client = MewsAPIClient(
                    client_token=config_adapter.client_token,
                    access_token=config_adapter.access_token,
                    base_url=config_adapter.api_base_url,
                )

                # Step 3: Determine time range for incremental fetch
                now = timezone.now()
                last_fetch_str = (integration.additional_info or {}).get("last_keycard_fetch")
                if last_fetch_str:
                    last_fetch = datetime.datetime.strptime(last_fetch_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=datetime.timezone.utc
                    )
                else:
                    last_fetch = now - datetime.timedelta(days=1)
                    logger.info("First fetch - using 1 day ago as start")

                # Step 4: Fetch access tokens
                start_utc = last_fetch.strftime("%Y-%m-%dT%H:%M:%SZ")
                end_utc = now.strftime("%Y-%m-%dT%H:%M:%SZ")

                logger.info(f"Fetching tokens updated from {start_utc} to {end_utc}")

                response = api_client.get_resource_access_tokens(
                    service_order_ids=reservation_ids,
                    updated_utc={"StartUtc": start_utc, "EndUtc": end_utc},
                    activity_states=["Active"],
                    limit=100,
                )

                all_tokens = response.get("ResourceAccessTokens", [])
                cursor = response.get("Cursor")

                # Handle pagination
                while cursor:
                    logger.info("  Fetching next page...")
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

                logger.info(f"  Found {len(all_tokens)} total token(s), {len(rfid_tokens)} RFID tag(s)")

                if not rfid_tokens:
                    logger.info("No RFID tags to publish")
                    # Still update last fetch timestamp
                    self._update_last_fetch(integration, now)
                    continue

                # Step 6: Assign keycards to devices
                assigned = self._assign_keycards(tenant, rfid_tokens, active_guests)
                total_published += assigned

                # Step 7: Update last fetch timestamp
                self._update_last_fetch(integration, now)

                # Display sample data
                if rfid_tokens:
                    logger.info("\n  Sample key card data:")
                    for idx, token in enumerate(rfid_tokens[:3], 1):
                        logger.info(f"    {idx}. ID: {token.get('Id', 'N/A')[:20]}...")
                        logger.info(f"       Value: {token.get('Value', 'N/A')}")
                        logger.info(
                            f"Valid: {token.get('ValidityStartUtc', 'N/A')} → {token.get('ValidityEndUtc', 'N/A')}"
                        )
                        logger.info(f"       Reservation: {token.get('ServiceOrderId', 'N/A')[:20]}...")

            except Exception as e:
                logger.exception(f"Error processing tenant {tenant.title}")
                logger.warning(self.style.ERROR(f"  ✗ Failed: {str(e)}"))
                continue

        logger.info(f"\n{'=' * 60}")
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

    def _update_last_fetch(self, integration: Integration, fetch_time: datetime.datetime) -> None:
        try:
            additional_info = integration.additional_info or {}
            additional_info["last_keycard_fetch"] = fetch_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            integration.additional_info = additional_info
            integration.save(update_fields=["additional_info"])
            logger.info(f"Updated last_keycard_fetch for tenant {integration.tenant.title}")
        except Exception as _:
            logger.exception(f"Failed to update last_keycard_fetch for tenant {integration.tenant.title}")
