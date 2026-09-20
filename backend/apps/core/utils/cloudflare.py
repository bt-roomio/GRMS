import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class CloudflareError(Exception):
    """Base class for every failure talking to the Cloudflare API."""


class CloudflareNotConfigured(CloudflareError):
    """CLOUDFLARE_API_TOKEN / CLOUDFLARE_ZONE_ID missing from the environment."""


class CloudflareAPIError(CloudflareError):
    """The API answered, but not with success."""

    def __init__(self, status_code, message, payload=None):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"Cloudflare API {status_code}: {message}")


class CloudflareUnavailable(CloudflareError):
    """Network-level failure, rate limit or a 5xx — worth retrying."""


class CloudflareClient:
    """
    DNS records of a single Cloudflare zone.
    """

    def __init__(
        self,
        token: str | None = None,
        zone_id: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = settings.CLOUDFLARE_API_URL.rstrip("/")
        self.token = token if token is not None else settings.CLOUDFLARE_API_TOKEN
        self.zone_id = zone_id if zone_id is not None else settings.CLOUDFLARE_ZONE_ID
        self.timeout = timeout if timeout is not None else settings.CLOUDFLARE_TIMEOUT

        if not self.token or not self.zone_id:
            raise CloudflareNotConfigured("CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID must both be set")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _zone_path(self, path: str = "") -> str:
        return f"zones/{self.zone_id}/{path.lstrip('/')}".rstrip("/")

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise CloudflareUnavailable(f"{method} {url} failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code == 429 or response.status_code >= 500:
            raise CloudflareUnavailable(f"{method} {url} answered {response.status_code}")

        if response.status_code >= 400 or not payload.get("success"):
            errors = payload.get("errors") or []
            message = "; ".join(str(error.get("message", error)) for error in errors) or response.text
            raise CloudflareAPIError(response.status_code, message, payload)

        return payload.get("result")

    def zone_name(self) -> str:
        """
        The zone's own domain. A record name outside it is taken as relative and
        gets the zone appended, so callers check before writing.
        """
        return (self._request("GET", self._zone_path()) or {}).get("name", "")

    def find_record(self, name: str, record_type: str = "CNAME") -> dict[str, Any] | None:
        records = self._request("GET", self._zone_path("dns_records"), params={"type": record_type, "name": name}) or []
        return records[0] if records else None

    def upsert_cname(self, name: str, target: str, comment: str = "") -> dict[str, Any]:
        """
        Point `name` at `target`, creating the record or fixing an existing one.

        DNS-only on purpose: the certificate comes from Let's Encrypt on nginx-proxy,
        and Universal SSL would not cover a name this deep anyway.
        """
        data = {"type": "CNAME", "name": name, "content": target, "ttl": 1, "proxied": False, "comment": comment}

        record = self.find_record(name)
        if record:
            return self._request("PATCH", self._zone_path(f"dns_records/{record['id']}"), json=data)
        return self._request("POST", self._zone_path("dns_records"), json=data)

    def delete_record(self, record_id: str) -> None:
        try:
            self._request("DELETE", self._zone_path(f"dns_records/{record_id}"))
        except CloudflareAPIError as exc:
            if exc.status_code != 404:
                raise
            logger.info("Cloudflare DNS record %s is already gone", record_id)
