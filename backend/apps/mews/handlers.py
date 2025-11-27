import logging
from typing import Any, Dict, List, Optional

from mews.client import MewsAPIClient
from mews.models import MewsConfiguration

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq

logger = logging.getLogger(__name__)


class ReservationEventHandler:
    """Handles reservation events from Mews WebSocket"""

    # Event type mapping
    EVENT_TYPE_MAPPING = {
        "Started": "checkin",
        "Processed": "checkout",
        "Confirmed": "checkout",
    }

    def __init__(self, mews_config: MewsConfiguration):
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
            base_url=mews_config.api_base_url,  # pyright: ignore
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

            logger.info(f"Processing {event_type} for reservation {reservation_id}")
            self._process_reservation({"event_type": event_type, **event})

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

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

        Args:
            reservation_id: Mews reservation ID

        Returns:
            Reservation details or None if not found
        """
        response = self.api_client.get_reservations_by_ids([reservation_id])
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

        return customers[0]

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
            "first_name": customer.get("FirstName", ""),
            "last_name": customer.get("LastName", ""),
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

        if customer.get("BirthDate"):
            standardized_data["birthday"] = customer.get("BirthDate")

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

    def _process_reservation(self, event: Dict[str, Any]) -> None:
        """
        Process reservation event - fetch data from Mews and publish to RabbitMQ

        Args:
            event: Event dictionary with event_type already set
        """
        try:
            required_fields = ["Id", "AssignedResourceId", "StartUtc", "EndUtc"]
            try:
                self._validate_required_fields(event, required_fields)
            except ValueError as e:
                logger.warning(f"Validation failed: {e}")
                return

            reservation_id = event["Id"]
            resource_id = event["AssignedResourceId"]

            logger.info(f"Processing {event.get('event_type')} for reservation {reservation_id}")

            reservation = self._fetch_reservation(reservation_id)
            if not reservation:
                return

            resource = self._fetch_resource(resource_id)
            if not resource:
                return

            customer_id = reservation.get("AccountId")
            if not customer_id:
                logger.error(f"No AccountId found in reservation {reservation_id}")
                return

            customer = self._fetch_customer(customer_id)
            if not customer:
                return

            room_number = resource.get("Name", "")
            standardized_data = self._build_standardized_data(
                event=event,
                customer=customer,
                room_number=room_number,
                reservation_id=reservation_id,
                resource_id=resource_id,
            )

            self._publish_to_rabbitmq(standardized_data)

        except Exception as e:
            logger.error(f"Error processing reservation: {e}", exc_info=True)
