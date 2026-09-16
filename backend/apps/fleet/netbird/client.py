import logging
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

from fleet.netbird.exceptions import (
    NetBirdAPIError,
    NetBirdNotConfigured,
    NetBirdUnavailable,
)

logger = logging.getLogger(__name__)


class NetBirdClient:
    """
    Thin wrapper over the NetBird management REST API.

    A phonebook, nothing more: which peers exist, their groups, whether they
    are connected. It cannot reach or run anything on a peer — that is
    `fleet.utils.ssh`.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url if base_url is not None else settings.NETBIRD_API_URL).rstrip("/")
        self.token = token if token is not None else settings.NETBIRD_PAT
        self.timeout = timeout if timeout is not None else settings.NETBIRD_TIMEOUT

        if not self.base_url or not self.token:
            raise NetBirdNotConfigured("NETBIRD_API_URL and NETBIRD_PAT must both be set")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Token {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise NetBirdUnavailable(f"{method} {url} failed: {exc}") from exc

        if response.status_code >= 400:
            try:
                payload = response.json()
                message = payload.get("message") or payload.get("detail") or response.text
            except ValueError:
                payload, message = None, response.text
            raise NetBirdAPIError(response.status_code, message, payload)

        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise NetBirdAPIError(response.status_code, f"non-JSON response: {exc}") from exc

    def list_peers(self, group_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        All peers, optionally narrowed to one group.

        The API has no group filter, so the narrowing happens here.
        """
        peers = self._request("GET", "/peers") or []

        if not group_id:
            return peers

        return [peer for peer in peers if any(group.get("id") == group_id for group in peer.get("groups") or [])]

    def get_peer(self, peer_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/peers/{peer_id}")

    def delete_peer(self, peer_id: str) -> None:
        self._request("DELETE", f"/peers/{peer_id}")

    def create_setup_key(
        self,
        name: str,
        auto_groups: Optional[List[str]] = None,
        usage_limit: int = 1,
        expires_in: Optional[int] = None,
        ephemeral: bool = False,
    ) -> Dict[str, Any]:
        """
        Mint a setup key. The plaintext `key` is returned once, at creation,
        and is never retrievable again.
        """
        body = {
            "name": name,
            "type": "one-off" if usage_limit == 1 else "reusable",
            "expires_in": (expires_in if expires_in is not None else settings.NETBIRD_SETUP_KEY_TTL),
            "revoked": False,
            "auto_groups": auto_groups or [],
            "usage_limit": usage_limit,
            "ephemeral": ephemeral,
        }
        return self._request("POST", "/setup-keys", json=body)

    def revoke_setup_key(self, key_id: str) -> Dict[str, Any]:
        return self._request("PUT", f"/setup-keys/{key_id}", json={"revoked": True})

    def delete_setup_key(self, key_id: str) -> None:
        """
        Remove a setup key outright, used or unused.

        Revoking leaves the row behind; enrollment wants the key list to stay
        one row per live node.
        """
        self._request("DELETE", f"/setup-keys/{key_id}")

    def list_setup_keys(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/setup-keys") or []

    def list_groups(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/groups") or []

    def get_group_id_by_name(self, name: str) -> Optional[str]:
        for group in self.list_groups():
            if group.get("name") == name:
                return group.get("id")
        return None
