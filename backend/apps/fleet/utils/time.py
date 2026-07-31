from django.utils.dateparse import parse_datetime


def to_mil_sec(value):
    """
    NetBird timestamps are RFC3339 strings; the rest of GRMS stores Unix epoch
    in milliseconds. Returns None for anything unparseable.
    """
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return int(value)

    parsed = parse_datetime(str(value))
    if parsed is None:
        return None
    return int(parsed.timestamp() * 1000)
