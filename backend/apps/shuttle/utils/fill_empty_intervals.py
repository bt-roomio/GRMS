import datetime
import re

from dateutil.relativedelta import relativedelta
from django.utils import timezone


def parse_interval(interval_str):
    pattern = (
        r"^(?:(?P<qty>\d+)\s+)?" r"(?P<unit>second|seconds|minute|minutes|hour|hours|day|days|week|weeks|month|year)$"
    )
    match = re.match(pattern, interval_str)
    if not match:
        raise ValueError(f"Invalid interval: {interval_str}")
    qty = int(match.group("qty") or 1)
    unit = match.group("unit").rstrip("s")

    # month/year singular only
    if unit in ("month", "year") and match.group("qty"):
        raise ValueError("Use 'month' or 'year' without quantity")
    return (unit in ("month", "year")), {unit + "s": qty}


def fill_missing_intervals(data, interval_str, start_ts, limit, key_name):
    if not interval_str or not start_ts or not limit:
        return []

    if isinstance(start_ts, str):
        dt = datetime.datetime.strptime(start_ts, "%Y-%m-%d %H:%M:%S")
        start_ts = timezone.make_aware(dt, timezone.get_current_timezone())

    use_rd, delta_kwargs = parse_interval(interval_str)
    result = []

    def make_key(dt):
        return dt.timestamp()

    if data and len(data) == 1 and data[0]["ts"] < start_ts:
        data[0]["ts"] = start_ts

    data_by_key = {make_key(rec["ts"]): rec for rec in data}

    current = start_ts
    last_known = None

    for i in range(limit):
        key = make_key(current)
        record = data_by_key.get(key)
        if i == 0 and data_by_key:
            record = next(iter(data_by_key.values()), None)

        if record:
            result.append(record)
            last_known = record
        else:
            result.append(
                {
                    "ts": current,
                    "value": last_known["value"] if last_known else 0,
                    "count": 0,
                    "key_name": last_known["key_name"] if last_known else key_name,
                }
            )
        if use_rd:
            current = current + relativedelta(**delta_kwargs)
        else:
            current = current + datetime.timedelta(**delta_kwargs)

    return result
