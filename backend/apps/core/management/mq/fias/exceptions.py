class LookupFailure(Exception):
    """Raised when a FIAS handler cannot resolve a required entity (room, guest, reader, card)."""
