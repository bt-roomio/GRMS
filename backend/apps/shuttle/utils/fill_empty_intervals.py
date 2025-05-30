import datetime
import re
from datetime import timedelta

from dateutil.relativedelta import relativedelta


def parse_interval(interval_str):
    pattern = (
        r"^(?:(?P<qty>\d+)\s+)?" r"(?P<unit>second|seconds|minute|minutes|hour|hours|day|days|week|weeks|month|year)$"
    )
    match = re.match(pattern, interval_str)
    if not match:
        raise ValueError(f"Invalid interval: {interval_str}")
    qty = int(match.group("qty") or 1)
    unit = match.group("unit").rstrip("s")

    if unit in ("month", "year") and match.group("qty"):
        raise ValueError("Use 'month' or 'year' without quantity")

    return (True if unit in ("month", "year") else False), {unit + "s": qty}


def fill_missing_intervals(data, interval_str, start_ts, limit):
    if not interval_str or not start_ts or not limit:
        return []

    if start_ts and isinstance(start_ts, str):
        start_ts = datetime.datetime.strptime(start_ts, "%Y-%m-%d %H:%M:%S")

    use_rd, delta_kwargs = parse_interval(interval_str)
    result = []

    # Index incoming data by timestamp
    data_by_ts = {record["ts"]: record for record in data}
    current_ts = start_ts
    last_known = None

    for _ in range(limit):
        record = data_by_ts.get(current_ts)
        if record:
            result.append(record)
            last_known = record
        else:
            result.append(
                {
                    "ts": current_ts,
                    "value": last_known["value"] if last_known else 0,
                    "count": 0,
                    "key_name": last_known["key_name"] if last_known else None,
                }
            )
        current_ts += relativedelta(**delta_kwargs) if use_rd else timedelta(**delta_kwargs)  # pyright: ignore

    return result
