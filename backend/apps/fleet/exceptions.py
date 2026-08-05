class FleetError(Exception):
    """Base class for fleet execution failures."""


class FleetNodeNotEnrolled(FleetError):
    """The node has no mesh IP yet — it has never joined, or never been polled."""


class FleetNodeUnreachable(FleetError):
    """The node is enrolled but the SSH connection could not be established."""


class FleetHostKeyMismatch(FleetError):
    """
    The node presented a different SSH host key than the one pinned on first
    connect. Treated as hostile: the connection is refused, never re-pinned.
    """


class FleetKeyUnavailable(FleetError):
    """The fleet private key is missing or unreadable on this server."""


class FleetPathRejected(FleetError):
    """
    The requested destination escapes ``FLEET_UPLOAD_ROOT``, or the node resolved
    it to somewhere outside that tree. Nothing is transferred.
    """


class FleetTransferFailed(FleetError):
    """The connection held but the file could not be written to the node."""
