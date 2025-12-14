"""
Simple Mews API Client for GRMS
Handles basic API operations needed for reservation sync
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class MewsAPIClient:
    """Lightweight client for Mews Connector API v1"""

    def __init__(
        self,
        client_token: str,
        access_token: str,
        base_url: str,
        client_name: str = "GRMS 1.0.0",
    ):
        """
        Initialize Mews API Client

        Args:
            client_token: Application ClientToken
            access_token: Property-specific AccessToken
            base_url: API base URL (from MewsConfiguration.api_base_url)
            client_name: Application name and version
        """
        self.client_token = client_token
        self.access_token = access_token
        self.base_url = base_url
        self.client_name = client_name
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Make a request to Mews API with retry logic

        Args:
            endpoint: API endpoint (e.g., "reservations/getAll")
            params: Additional parameters
            max_retries: Maximum retry attempts

        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/{endpoint}"

        # Build payload with auth credentials
        payload = {
            "ClientToken": self.client_token,
            "AccessToken": self.access_token,
            "Client": self.client_name,
        }

        if params:
            payload.update(params)

        for attempt in range(max_retries):
            response = self.session.post(url, json=payload, timeout=30)
            try:
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 30))
                    logger.warning(f"Rate limited. Waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()

                return response.json() if response.content else {}

            except requests.exceptions.HTTPError as e:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("Message", str(e))
                request_id = error_data.get("RequestId")

                logger.error(f"Mews API Error: {error_msg} (Request ID: {request_id})")

                # Don't retry client errors
                if response.status_code in [400, 401, 403, 404]:
                    raise

                # Retry server errors with backoff
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time}s ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    raise

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    time.sleep(wait_time)
                else:
                    raise

        raise Exception(f"Max retries ({max_retries}) exceeded")

    def get_reservations_by_ids(
        self,
        reservation_ids: List[str],
        extent: Optional[Dict[str, bool]] = None,
        include_companions: bool = False,
    ) -> Dict[str, Any]:
        """
        Get specific reservations by IDs (used after WebSocket events)

        Args:
            reservation_ids: List of reservation UUIDs
            extent: Optional extent configuration
            include_companions: If True, uses old API endpoint that returns CompanionIds field

        Returns:
            Response with Reservations, Customers, etc.
        """
        params = {
            "ReservationIds": reservation_ids,
            "Limitation": {"Cursor": None, "Count": 10},
        }

        if extent:
            params["Extent"] = extent  # pyright: ignore
        else:
            # Default extent - get all related data
            params["Extent"] = {  # pyright: ignore
                "Reservations": True,
                "ReservationGroups": False,
                "Customers": True,
            }

        # Use old API endpoint if we need CompanionIds field
        # New API (2023-06-06) doesn't return CompanionIds, CustomerId, OwnerId
        # Old API returns CompanionIds which includes all guests (owner + companions)
        endpoint = "reservations/getAll" if include_companions else "reservations/getAll/2023-06-06"

        return self._make_request(endpoint, params)

    def get_all_customers(self, params={}):
        return self._make_request("customers/getAll", params)

    def get_customer_by_ids(self, customer_ids: list[str], params={}):
        if not customer_ids or not isinstance(customer_ids, list):
            raise ValueError("customer_ids must be a non-empty list")
        return self.get_all_customers(params={"CustomerIds": customer_ids, **params})

    def get_all_reservations(
        self,
        start_utc: Optional[str] = None,
        end_utc: Optional[str] = None,
        updated_utc: Optional[Dict[str, str]] = None,
        extent: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        """
        Get all reservations with filters

        Args:
            start_utc: Start date (ISO 8601)
            end_utc: End date (ISO 8601)
            updated_utc: Filter by update time {"StartUtc": "...", "EndUtc": "..."}
            extent: Optional extent configuration
            include_companions: If True, uses old API endpoint that returns CompanionIds field

        Returns:
            Response with reservations
        """
        params: dict[str, Any] = {
            "Limitation": {"Cursor": None, "Count": 100},
        }

        if start_utc and end_utc:
            params["CollidingUtc"] = {"StartUtc": start_utc, "EndUtc": end_utc}

        if updated_utc:
            params["UpdatedUtc"] = updated_utc

        if extent:
            params["Extent"] = extent
        else:
            params["Extent"] = {
                "Reservations": True,
                "ReservationGroups": False,
                "Customers": True,
            }

        return self._make_request("reservations/getAll/2023-06-06", params)

    def get_configuration(self) -> Dict[str, Any]:
        """Get enterprise configuration"""
        return self._make_request("configuration/get")

    def get_services(self) -> Dict[str, Any]:
        """
        Get all services for the enterprise

        Returns:
            Response with Services list containing ServiceIds
        """
        params = {
            "Extent": {
                "Services": True,
            }
        }
        return self._make_request("services/getAll", params)

    def get_resources(
        self,
        resource_ids: Optional[List[str]] = None,
        extent: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        """
        Get resources (rooms, spaces, etc.)

        Args:
            service_ids: List of service UUIDs (required by Mews API)
            resource_ids: Optional list of specific resource UUIDs to fetch
            extent: Optional extent configuration

        Returns:
            Response with Resources, ResourceCategories, etc.
        """
        params = {}

        if resource_ids:
            params["ResourceIds"] = resource_ids

        if extent:
            params["Extent"] = extent  # pyright: ignore
        else:
            params["Extent"] = {  # pyright: ignore
                "Resources": True,
                "ResourceCategories": True,
                "ResourceCategoryAssignments": True,
                "ResourceCategoryImageAssignments": True,
                "ResourceFeatures": True,
                "ResourceFeatureAssignments": True,
                "Inactive": False,
            }

        return self._make_request("resources/getAll", params)

    def get_resource_by_id(
        self,
        # service_ids: List[str],
        resource_id: str,
        extent: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        """
        Get a single resource by ID

        Args:
            service_ids: List of service UUIDs (required by Mews API)
            resource_id: Resource UUID
            extent: Optional extent configuration

        Returns:
            Response with the resource data
        """
        return self.get_resources(resource_ids=[resource_id], extent=extent)

    def get_customers_by_resource_id(
        self,
        resource_id: str,
        start_utc: Optional[str] = None,
        end_utc: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get customer information for a specific resource (room)

        Args:
            resource_id: Resource UUID (room ID)
            start_utc: Start date filter (ISO 8601)
            end_utc: End date filter (ISO 8601)

        Returns:
            Response with Reservations, Customers, and ResourceId mapping
        """
        params = {
            "AssignedResourceIds": [resource_id],
            "Extent": {
                "Reservations": True,
                "Customers": True,
                "ReservationGroups": False,
            },
        }

        if start_utc and end_utc:
            params["StartUtc"] = start_utc
            params["EndUtc"] = end_utc

        return self._make_request("reservations/getAll", params)

    def search_customers(
        self,
        name: Optional[str] = None,
        resource_id: Optional[str] = None,
        customer_ids: Optional[List[str]] = None,
        emails: Optional[List[str]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Search customers using Mews customers/search API

        Args:
            name: Customer name to search
            resource_id: Resource UUID to find customer in that room
            customer_ids: List of customer UUIDs
            emails: List of email addresses
            limit: Maximum number of results (default 100)

        Returns:
            Response with Customers list
        """
        params = {
            "Limitation": {
                "Count": limit,
            },
        }

        if name:
            params["Name"] = name  # pyright: ignore

        if customer_ids:
            params["CustomerIds"] = customer_ids  # pyright: ignore

        if emails:
            params["Emails"] = emails  # pyright: ignore

        if resource_id:
            params["ResourceId"] = resource_id  # pyright: ignore

        return self._make_request("customers/search", params)

    def get_resource_access_tokens(
        self,
        colliding_utc: Optional[Dict[str, str]] = None,
        updated_utc: Optional[Dict[str, str]] = None,
        resource_access_token_ids: Optional[List[str]] = None,
        service_order_ids: Optional[List[str]] = None,
        activity_states: Optional[List[str]] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get all resource access tokens (key cards) from Mews

        Args:
            colliding_utc: Time interval for token validity {"StartUtc": "...", "EndUtc": "..."}
            updated_utc: Time interval for modification dates {"StartUtc": "...", "EndUtc": "..."}
            resource_access_token_ids: List of specific token IDs (up to 1000)
            service_order_ids: List of reservation IDs (up to 1000)
            activity_states: Filter by Active/Deleted status (e.g., ["Active"])
            cursor: Pagination cursor from previous response (optional)
            limit: Maximum number of results per request (default 100)

        Returns:
            Response with ResourceAccessTokens list and pagination cursor

        Note:
            At least one filter parameter (colliding_utc, updated_utc, resource_access_token_ids,
            or service_order_ids) must be provided.
        """
        params: Dict[str, Any] = {
            "Limitation": {
                "Cursor": cursor,
                "Count": limit,
            },
        }

        if colliding_utc:
            params["CollidingUtc"] = colliding_utc

        if updated_utc:
            params["UpdatedUtc"] = updated_utc

        if resource_access_token_ids:
            params["ResourceAccessTokenIds"] = resource_access_token_ids

        if service_order_ids:
            params["ServiceOrderIds"] = service_order_ids

        if activity_states:
            params["ActivityStates"] = activity_states

        return self._make_request("resourceAccessTokens/getAll", params)
