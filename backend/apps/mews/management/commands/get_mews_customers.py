"""
Django Management Command: Get Mews Customers
Get customers for a specific Reservation or Resource (Room) from Mews API
"""

import json
import logging

from django.core.management.base import BaseCommand
from mews.client import MewsAPIClient
from mews.models import MewsConfiguration

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Get customers from Mews for a specific Reservation or Resource"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-id",
            type=str,
            required=True,
            help="Tenant ID",
        )
        parser.add_argument(
            "--reservation-id",
            type=str,
            help="Mews Reservation ID (UUID)",
        )
        parser.add_argument(
            "--resource-id",
            type=str,
            help="Mews Resource ID (Room UUID)",
        )
        parser.add_argument(
            "--pretty",
            action="store_true",
            help="Pretty print JSON output",
        )

    def handle(self, *args, **options):
        tenant_id = options["tenant_id"]
        reservation_id = options.get("reservation_id")
        resource_id = options.get("resource_id")
        pretty = options.get("pretty", False)

        # Validation
        if not reservation_id and not resource_id:
            self.stdout.write(self.style.ERROR("Error: You must provide either --reservation-id or --resource-id"))
            return

        # Get Mews configuration for tenant
        try:
            config = MewsConfiguration.objects.get(tenant__id=tenant_id, is_active=True)
        except MewsConfiguration.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No active Mews configuration found for tenant ID: {tenant_id}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Using Mews configuration for tenant: {config.tenant.title}"))
        self.stdout.write(f"Environment: {config.environment}")
        self.stdout.write(f"API URL: {config.api_base_url}\n")

        # Initialize API client
        client = MewsAPIClient(
            client_token=config.client_token,
            access_token=config.access_token,
            base_url=config.api_base_url,
        )

        try:
            if reservation_id:
                self._get_customers_by_reservation(client, reservation_id, pretty)
            elif resource_id:
                self._get_customers_by_resource(client, resource_id, pretty)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            logger.error(f"Error getting customers: {e}", exc_info=True)

    def _get_customers_by_reservation(self, client: MewsAPIClient, reservation_id: str, pretty: bool):
        """Get customers for a specific reservation"""
        self.stdout.write(self.style.SUCCESS(f"Fetching customers for Reservation ID: {reservation_id}\n"))

        # Get reservation with customers
        response = client.get_reservations_by_ids(
            reservation_ids=[reservation_id],
            extent={
                "Reservations": True,
                "ReservationGroups": True,
                "Customers": True,
            },
        )

        reservations = response.get("Reservations", [])
        customers = response.get("Customers", [])

        if not reservations:
            self.stdout.write(self.style.ERROR(f"No reservation found with ID: {reservation_id}"))
            return

        reservation = reservations[0]

        # Display reservation info
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("RESERVATION INFORMATION"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(f"Reservation ID: {reservation.get('Id')}")
        self.stdout.write(f"State: {reservation.get('State')}")
        self.stdout.write(f"Account ID: {reservation.get('AccountId')}")
        self.stdout.write(f"Assigned Resource ID: {reservation.get('AssignedResourceId')}")
        self.stdout.write(f"Start UTC: {reservation.get('StartUtc')}")
        self.stdout.write(f"End UTC: {reservation.get('EndUtc')}")
        self.stdout.write(f"Type: {reservation.get('Type')}")
        self.stdout.write("")

        # Display customers
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS(f"CUSTOMERS ({len(customers)} found)"))
        self.stdout.write(self.style.SUCCESS("=" * 80))

        if customers:
            for idx, customer in enumerate(customers, 1):
                self.stdout.write(f"\n--- Customer #{idx} ---")
                self.stdout.write(f"ID: {customer.get('Id')}")
                self.stdout.write(f"Name: {customer.get('FirstName')} {customer.get('LastName')}")
                self.stdout.write(f"Title: {customer.get('Title')}")
                self.stdout.write(f"Email: {customer.get('Email')}")
                self.stdout.write(f"Phone: {customer.get('Phone')}")
                self.stdout.write(f"Language Code: {customer.get('LanguageCode')}")
                self.stdout.write(f"Nationality Code: {customer.get('NationalityCode')}")
                self.stdout.write(f"Birth Date: {customer.get('BirthDate')}")
        else:
            self.stdout.write(self.style.WARNING("No customers found for this reservation"))

        # Output full JSON if --pretty flag is set
        if pretty:
            self.stdout.write(f"\n{self.style.SUCCESS('=' * 80)}")
            self.stdout.write(self.style.SUCCESS("FULL JSON RESPONSE"))
            self.stdout.write(self.style.SUCCESS("=" * 80))
            self.stdout.write(json.dumps(response, indent=2, ensure_ascii=False))

    def _get_customers_by_resource(self, client: MewsAPIClient, resource_id: str, pretty: bool):
        """Get customers for a specific resource (room)"""
        self.stdout.write(self.style.SUCCESS(f"Fetching customers for Resource ID: {resource_id}\n"))

        # Method 1: Get customers by resource ID through reservations
        self.stdout.write(self.style.SUCCESS("Method 1: Via reservations/getAll"))
        response = client.get_customers_by_resource_id(resource_id=resource_id)

        reservations = response.get("Reservations", [])
        customers = response.get("Customers", [])

        # Also get resource details
        self.stdout.write(self.style.SUCCESS("\nFetching resource details..."))
        resource_response = client.get_resource_by_id(resource_id=resource_id)
        resources = resource_response.get("Resources", [])

        if resources:
            resource = resources[0]
            self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
            self.stdout.write(self.style.SUCCESS("RESOURCE (ROOM) INFORMATION"))
            self.stdout.write(self.style.SUCCESS("=" * 80))
            self.stdout.write(f"Resource ID: {resource.get('Id')}")
            self.stdout.write(f"Name: {resource.get('Name')}")
            self.stdout.write(f"State: {resource.get('State')}")
            self.stdout.write(f"Type: {resource.get('Type')}")
            self.stdout.write("")

        # Display reservations
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS(f"RESERVATIONS ({len(reservations)} found)"))
        self.stdout.write(self.style.SUCCESS("=" * 80))

        if reservations:
            for idx, reservation in enumerate(reservations, 1):
                self.stdout.write(f"\n--- Reservation #{idx} ---")
                self.stdout.write(f"ID: {reservation.get('Id')}")
                self.stdout.write(f"State: {reservation.get('State')}")
                self.stdout.write(f"Account ID: {reservation.get('AccountId')}")
                self.stdout.write(f"Start UTC: {reservation.get('StartUtc')}")
                self.stdout.write(f"End UTC: {reservation.get('EndUtc')}")
        else:
            self.stdout.write(self.style.WARNING("No reservations found for this resource"))

        # Display customers
        self.stdout.write(f"\n{self.style.SUCCESS('=' * 80)}")
        self.stdout.write(self.style.SUCCESS(f"CUSTOMERS ({len(customers)} found)"))
        self.stdout.write(self.style.SUCCESS("=" * 80))

        if customers:
            for idx, customer in enumerate(customers, 1):
                self.stdout.write(f"\n--- Customer #{idx} ---")
                self.stdout.write(f"ID: {customer.get('Id')}")
                self.stdout.write(f"Name: {customer.get('FirstName')} {customer.get('LastName')}")
                self.stdout.write(f"Title: {customer.get('Title')}")
                self.stdout.write(f"Email: {customer.get('Email')}")
                self.stdout.write(f"Phone: {customer.get('Phone')}")
                self.stdout.write(f"Language Code: {customer.get('LanguageCode')}")
                self.stdout.write(f"Nationality Code: {customer.get('NationalityCode')}")
                self.stdout.write(f"Birth Date: {customer.get('BirthDate')}")
        else:
            self.stdout.write(self.style.WARNING("No customers found for this resource"))

        # Method 2: Search customers by resource
        self.stdout.write(f"\n{self.style.SUCCESS('=' * 80)}")
        self.stdout.write(self.style.SUCCESS("Method 2: Via customers/search"))
        self.stdout.write(self.style.SUCCESS("=" * 80))

        search_response = client.search_customers(resource_id=resource_id)
        search_customers = search_response.get("Customers", [])

        self.stdout.write(f"Found {len(search_customers)} customers via search")

        # Output full JSON if --pretty flag is set
        if pretty:
            self.stdout.write(f"\n{self.style.SUCCESS('=' * 80)}")
            self.stdout.write(self.style.SUCCESS("FULL JSON RESPONSE (Method 1: reservations/getAll)"))
            self.stdout.write(self.style.SUCCESS("=" * 80))
            self.stdout.write(json.dumps(response, indent=2, ensure_ascii=False))

            self.stdout.write(f"\n{self.style.SUCCESS('=' * 80)}")
            self.stdout.write(self.style.SUCCESS("FULL JSON RESPONSE (Method 2: customers/search)"))
            self.stdout.write(self.style.SUCCESS("=" * 80))
            self.stdout.write(json.dumps(search_response, indent=2, ensure_ascii=False))
