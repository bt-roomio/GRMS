class NetBirdError(Exception):
    """Base class for every failure talking to the NetBird management API."""


class NetBirdNotConfigured(NetBirdError):
    """NETBIRD_API_URL / NETBIRD_PAT missing from the environment."""


class NetBirdAPIError(NetBirdError):
    """The management API answered, but not with success."""

    def __init__(self, status_code, message, payload=None):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"NetBird API {status_code}: {message}")


class NetBirdUnavailable(NetBirdError):
    """Network-level failure — timeout, DNS, connection refused."""
