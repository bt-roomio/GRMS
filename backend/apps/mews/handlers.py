import logging
from typing import Any, Dict, List, Optional

from mews.client import MewsAPIClient

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.date import datetime_to_unix
from main.models import Guest

logger = logging.getLogger(__name__)


class ReservationEventHandler:
    """Handles reservation events from Mews WebSocket"""

    # Event type mapping
    EVENT_TYPE_MAPPING = {
        "Confirmed": "reservation",
        "Started": "checkin",
        "Processed": "checkout",
        "Canceled": "canceled",
    }

    def __init__(self, mews_config):
        """
        Initialize handler

        Args:
            mews_config: MewsConfiguration instance for this tenant
        """
        self.mews_config = mews_config
        self.tenant = mews_config.tenant
        self.api_client = MewsAPIClient(
            client_token=mews_config.client_token,
            access_token=mews_config.access_token,
            base_url=mews_config.api_base_url,
        )

    def handle_event(self, event: Dict[str, Any]) -> None:
        """
        Process a reservation event from WebSocket

        Args:
            event: Event dictionary from WebSocket
        """
        try:
            logger.info(f"Received event: {event}")
            reservation_id = event.get("Id")
            state = event.get("State", "Unknown")

            if not reservation_id:
                logger.warning("Received event without reservation ID")
                return

            event_type = self.EVENT_TYPE_MAPPING.get(state)
            if not event_type:
                logger.info(f"Ignoring reservation {reservation_id} with unhandled state: {state}")
                return

            self._process_reservation({"event_type": event_type, **event})

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    def _process_reservation(self, event: Dict[str, Any]) -> None:
        """
        Process reservation event - fetch data from Mews and publish to RabbitMQ
        Processes all companions (guests) in the reservation

        Args:
            event: Event dictionary with event_type already set
        """
        try:
            required_fields = ["Id", "StartUtc", "EndUtc"]
            try:
                self._validate_required_fields(event, required_fields)
            except ValueError as e:
                logger.warning(f"Validation failed: {e}")
                return

            reservation_id = event["Id"]
            resource_id = event["AssignedResourceId"]

            reservation = self._fetch_reservation(reservation_id)
            if not reservation:
                return

            logger.info(f"Processing {event.get('event_type')} for reservation {reservation_id}")
            room_number = ""
            if resource_id:
                resource = self._fetch_resource(resource_id)
                room_number = resource.get("Name", "") if isinstance(resource, dict) else ""

            # Get all companion IDs from the reservation
            # CompanionIds includes all guests (owner + companions)
            companion_ids = reservation.get("CompanionIds", [])

            # Fallback to AccountId/CustomerId if CompanionIds is empty
            if not companion_ids:
                account_id = reservation.get("AccountId") or reservation.get("CustomerId")
                if not account_id:
                    logger.error(f"No CompanionIds or AccountId found in reservation {reservation_id}")
                    return
                companion_ids = [account_id]

            logger.info(f"Found {len(companion_ids)} companion(s) for reservation {reservation_id}")

            # Fetch all customers at once
            customers = self._fetch_customers(companion_ids)
            if not customers:
                logger.error(f"No customers found for reservation {reservation_id}")
                return

            # Process each customer (companion)
            for customer in customers:
                try:
                    standardized_data = self._build_standardized_data(
                        event=event,
                        customer=customer,
                        room_number=room_number,
                        reservation_id=reservation_id,
                        resource_id=resource_id,
                    )

                    self._publish_to_rabbitmq(standardized_data)

                except Exception as e:
                    logger.error(
                        f"Error processing customer {customer.get('Id')} for reservation {reservation_id}: {e}",
                        exc_info=True,
                    )

        except Exception as e:
            logger.error(f"Error processing reservation: {e}", exc_info=True)

    def _validate_required_fields(self, event: Dict[str, Any], required_fields: List[str]) -> None:
        """
        Validate that required fields exist and are not empty

        Args:
            event: Event dictionary from WebSocket
            required_fields: List of required field names

        Raises:
            ValueError: If any required field is missing or empty
        """
        missing_fields = []

        for field in required_fields:
            value = event.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(field)

        if missing_fields:
            error_msg = f"Missing or empty required field(s): {', '.join(missing_fields)}"
            logger.warning(f"{error_msg} in event: {event.get('Id', 'unknown')}")
            raise ValueError(error_msg)

    def _fetch_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch reservation details from Mews API
        Uses old API endpoint to get CompanionIds field

        Args:
            reservation_id: Mews reservation ID

        Returns:
            Reservation details or None if not found
        """
        response = self.api_client.get_reservations_by_ids(
            [reservation_id],
            include_companions=True,  # Use old API to get CompanionIds
        )
        reservations = response.get("Reservations", [])

        if not reservations:
            logger.error(f"No reservation found for ID: {reservation_id}")
            return None

        return reservations[0]

    def _fetch_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch resource (room) details from Mews API

        Args:
            resource_id: Mews resource ID

        Returns:
            Resource details or None if not found
        """
        response = self.api_client.get_resource_by_id(resource_id=resource_id)
        resources = response.get("Resources", [])

        if not resources:
            logger.error(f"No resource found for ID: {resource_id}")
            return None

        return resources[0]

    def _fetch_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch customer details from Mews API

        Args:
            customer_id: Mews customer/account ID

        Returns:
            Customer details or None if not found
        """
        response = self.api_client.get_customer_by_ids([customer_id])
        customers = response.get("Customers", [])

        if not customers:
            logger.error(f"No customer found for ID: {customer_id}")
            return None

        logger.info(f"Found customer: {customers[0].get('Id')}")
        return customers[0]

    def _fetch_customers(self, customer_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple customers details from Mews API

        Args:
            customer_ids: List of Mews customer/account IDs

        Returns:
            List of customer details (may be empty if none found)
        """
        if not customer_ids:
            return []

        response = self.api_client.get_customer_by_ids(customer_ids)
        customers = response.get("Customers", [])

        logger.info(f"Found {len(customers)} customers out of {len(customer_ids)} requested")
        return customers

    def _fetch_customers_by_resource(self, resource_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all customers for a specific resource (room) from Mews API
        Uses customers/search endpoint to get currently assigned customers

        Args:
            resource_id: Mews resource ID (room UUID)

        Returns:
            List of customer details (may be empty if none found)
        """
        response = self.api_client.search_customers(resource_id=resource_id)

        # customers/search returns a different structure with nested Customer objects
        search_results = response.get("Customers", [])
        customers = [result.get("Customer") for result in search_results if result.get("Customer")]

        logger.info(f"Found {len(customers)} customers for resource {resource_id}")
        return customers

    def _build_standardized_data(
        self,
        event: Dict[str, Any],
        customer: Dict[str, Any],
        room_number: str,
        reservation_id: str,
        resource_id: str,
    ) -> Dict[str, Any]:
        """
        Build standardized guest data from Mews API responses

        Args:
            event: Original event data
            customer: Customer data from Mews API
            room_number: Room number from resource
            reservation_id: Mews reservation ID
            resource_id: Mews resource ID

        Returns:
            Standardized data dictionary
        """
        standardized_data = {
            "hotel_id": str(self.mews_config.company_id),
            "first_name": customer.get("FirstName") or customer.get("LastName"),
            "last_name": customer.get("LastName", "") if customer.get("FirstName") else "",
            "room_number": room_number,
            "check_in_date": event.get("StartUtc"),
            "check_out_date": event.get("EndUtc"),
            "gender": customer.get("Title", ""),
            "language": "",
            "nationality": "",
            "birthday": "",
            "pms_id": customer.get("Id"),
            "type": event.get("Type"),
            "state": event.get("State"),
            "event_type": event.get("event_type"),
            "additional_info": {
                "mews_customer_id": customer.get("Id"),
                "mews_resource_id": resource_id,
                "mews_reservation_id": reservation_id,
            },
        }

        # Add optional customer fields if available
        if customer.get("LanguageCode") or customer.get("PreferredLanguageCode"):
            standardized_data["language"] = customer.get("LanguageCode") or customer.get("PreferredLanguageCode")

        if customer.get("NationalityCode"):
            standardized_data["nationality"] = customer.get("NationalityCode")

        if customer.get("BirthDate") is not None:
            standardized_data["birthday"] = datetime_to_unix(customer.get("BirthDate"))

        return standardized_data

    def _publish_to_rabbitmq(self, data: Dict[str, Any]) -> None:
        """
        Publish standardized guest data to RabbitMQ

        Args:
            data: Standardized guest data dictionary
        """
        try:
            # Create message in standard GRMS format
            message = {
                "topic": data.get("event_type", "unknown"),
                "data": data,
            }

            # Connect and send to RabbitMQ
            channel = connect_to_rabbitmq()
            send_to_rabbitmq(channel, message, routing_key="pmsMessages")
            channel.connection.close()

            logger.info(
                f"Published PMS message to RabbitMQ: {data.get('event_type')} for "
                f"guest {data.get('first_name')} {data.get('last_name')} in room {data.get('room_number')}"
            )

        except Exception as e:
            logger.error(f"Error publishing to RabbitMQ: {e}", exc_info=True)
            # Don't raise - we don't want to fail check-in/check-out if RabbitMQ fails

    def sync_reservations(self, start_utc: str, end_utc: str) -> Dict[str, Any]:
        """
        Sync reservations from Mews for a specific time period
        Handles check-in, check-out, and guest move scenarios

        Args:
            start_utc: Start date in ISO 8601 format (e.g., "2024-01-01T00:00:00Z")
            end_utc: End date in ISO 8601 format (e.g., "2024-01-02T00:00:00Z")

        Returns:
            Dictionary with sync statistics:
            {
                "total": int,
                "checked_in": int,
                "checked_out": int,
                "skipped": int,
                "errors": int
            }
        """
        stats = {
            "total": 0,
            "checked_in": 0,
            "checked_out": 0,
            "skipped": 0,
            "errors": 0,
        }

        try:
            logger.info(f"Starting reservation sync for period {start_utc} to {end_utc}")

            # Fetch all reservations for the time period
            # Use old API to get CompanionIds field
            response = self.api_client.get_all_reservations(
                start_utc=start_utc,
                end_utc=end_utc,
                extent={
                    "Reservations": True,
                    "ReservationGroups": False,
                    "Customers": True,
                },
            )

            reservations = response.get("Reservations", [])

            stats["total"] = len(reservations)
            logger.info(f"Found {stats['total']} reservations to process")

            # Process each reservation
            for reservation in reservations:
                try:
                    self._process_reservation_sync(reservation, stats)
                except Exception as e:
                    logger.error(f"Error processing reservation {reservation.get('Id')}: {e}", exc_info=True)
                    stats["errors"] += 1

            logger.info(
                f"Sync completed: {stats['checked_in']} checked in, "
                f"{stats['checked_out']} checked out, "
                f"{stats['skipped']} skipped, "
                f"{stats['errors']} errors"
            )

            return stats

        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            return {"error": str(e), **stats}

    def _check_for_guest_move(
        self,
        customer_id: str,
        room_number: str,
    ) -> Optional[Guest]:
        """
        Check if guest already exists with different room (guest move scenario)

        Args:
            customer_id: Mews customer ID (pms_id)
            room_number: New room number

        Returns:
            Guest instance if it's a room move, None otherwise
        """
        try:
            guest = Guest.objects.get(
                pms_id=customer_id,
                is_active=True,
            )

            # Guest exists - check if room is different
            if guest.room and guest.room.number != room_number:
                logger.info(
                    f"→ Detected guest move: {guest.name} {guest.lastname} "
                    f"from room {guest.room.number} to {room_number}"
                )
                return guest

            # Guest exists in same room - skip
            logger.info(f"Guest {guest.name} {guest.lastname} already in room {room_number}")
            return None

        except Guest.DoesNotExist:
            # New guest - proceed with check-in
            return None

    def _checked_out_from_roomio(self, customer_id: str, reservation_id: str) -> bool:
        """
        Check if guest was checked out from ROOMIO side

        Args:
            customer_id: Mews customer ID (pms_id)
            reservation_id: Mews reservation ID (for logging)

        Returns:
            True if guest was checked out from ROOMIO, False otherwise
        """
        try:
            # Look for inactive guest with this pms_id who was checked out from ROOMIO
            guest = Guest.objects.filter(
                pms_id=customer_id,
                is_active=False,
                checkout_by=Guest.CHECKOUT_BY.ROOMIO,
            ).first()

            if guest:
                logger.info(
                    f"Guest {guest.name} {guest.lastname} (pms_id={customer_id}) "
                    f"was checked out from ROOMIO - skipping check-in for reservation {reservation_id}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking checkout source for customer {customer_id}: {e}", exc_info=True)
            return False

    def _process_reservation_sync(self, reservation: Dict[str, Any], stats: Dict[str, Any]) -> None:
        """
        Process a single reservation during sync
        Handles check-in, check-out, and guest move scenarios
        Processes all companions (guests) in the reservation

        Args:
            reservation: Reservation data from Mews API
            stats: Statistics dictionary to update
        """
        reservation_id = reservation.get("Id")
        state = reservation.get("State", "")
        resource_id = reservation.get("AssignedResourceId")

        if not all([reservation_id, state, resource_id]):
            logger.info(
                f"Skipping reservation {reservation_id}: missing required fields "
                f"(state={state}, resource={resource_id})"
            )
            stats["skipped"] += 1
            return

        event_type = self.EVENT_TYPE_MAPPING.get(state)
        if not event_type:
            logger.info(f"Ignoring reservation {reservation_id} with unhandled state: {state}")
            return

        # Get all companion IDs from the reservation
        companion_ids = reservation.get("CompanionIds", [])

        # Fallback to AccountId/CustomerId if CompanionIds is empty
        if not companion_ids:
            customer_id = reservation.get("AccountId") or reservation.get("CustomerId")
            if not customer_id:
                logger.warning(f"No CompanionIds or AccountId found for reservation {reservation_id}")
                stats["errors"] += 1
                return
            companion_ids = [customer_id]

        logger.info(f"Found {len(companion_ids)} companion(s) for reservation {reservation_id}")

        # Fetch all customers at once
        customers = self._fetch_customers(companion_ids)
        if not customers:
            logger.warning(f"No customers found for reservation {reservation_id}")
            stats["errors"] += 1
            return

        # Fetch resource (room) details
        resource = self._fetch_resource(resource_id)  # ty: ignore
        if not resource:
            logger.warning(f"Resource {resource_id} not found for reservation {reservation_id}")
            stats["errors"] += 1
            return

        room_number = resource.get("Name", "")

        # Build event data
        event_data = {
            "Id": reservation_id,
            "AssignedResourceId": resource_id,
            "StartUtc": reservation.get("StartUtc"),
            "EndUtc": reservation.get("EndUtc"),
            "State": state,
            "Type": reservation.get("Type"),
            "event_type": event_type,
        }

        # Process each customer (companion)
        processed_count = 0
        for customer in customers:
            try:
                customer_id = customer.get("Id")

                # Check for guest move (only for check-in events)
                if event_type == "checkin":
                    # Skip check-in if guest was checked out from ROOMIO
                    if self._checked_out_from_roomio(customer_id, reservation_id):  # ty: ignore
                        logger.info(
                            f"Skipping check-in for {customer.get('FirstName')} {customer.get('LastName')} - "
                            f"guest was checked out from ROOMIO"
                        )
                        stats["skipped"] += 1
                        continue

                    existing_guest = self._check_for_guest_move(customer_id, room_number)  # ty: ignore
                    if existing_guest:
                        # This is a guest move, not a new check-in
                        # The pms_handler will handle the move when it receives the message
                        logger.info(
                            f"Detected guest move for {customer.get('FirstName')} {customer.get('LastName')}: "
                            f"room {existing_guest.room.number if existing_guest.room else 'N/A'} → {room_number}"
                        )
                        # Still publish as check-in - pms_handler will detect it's a move

                # Build standardized data
                standardized_data = self._build_standardized_data(
                    event=event_data,
                    customer=customer,
                    room_number=room_number,
                    reservation_id=reservation_id,  # ty: ignore
                    resource_id=resource_id,  # ty: ignore
                )

                logger.info(f"Standardized data for customer {customer_id}: {standardized_data}")

                # Publish to RabbitMQ
                self._publish_to_rabbitmq(standardized_data)
                processed_count += 1

                logger.info(
                    f"Processed {event_type} for reservation {reservation_id}: "
                    f"{customer.get('FirstName')} {customer.get('LastName')} in room {room_number}"
                )

            except Exception as e:
                logger.error(
                    f"Error processing customer {customer.get('Id')} for reservation {reservation_id}: {e}",
                    exc_info=True,
                )
                stats["errors"] += 1

        # Update stats (count reservation once, not per customer)
        if processed_count > 0:
            if event_type == "checkin":
                stats["checked_in"] += 1
            elif event_type == "checkout":
                stats["checked_out"] += 1
