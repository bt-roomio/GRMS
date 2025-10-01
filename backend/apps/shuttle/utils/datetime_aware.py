from datetime import datetime
from datetime import timezone as dt_timezone

from django.utils import timezone


def to_datetime_aware(value, tz=None):
    tz = tz or dt_timezone.utc

    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value, tz)

    if isinstance(value, (int, float)):
        ts_sec = value / 1000 if value > 1e12 else value
        return datetime.fromtimestamp(ts_sec, tz=dt_timezone.utc)

    if isinstance(value, str):
        s = value.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return dt if timezone.is_aware(dt) else timezone.make_aware(dt, tz)

    raise TypeError(f"Unsupported ts type: {type(value)}")
