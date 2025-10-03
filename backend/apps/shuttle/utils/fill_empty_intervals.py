import datetime
import re

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

    # month/year singular only
    if unit in ("month", "year") and match.group("qty"):
        raise ValueError("Use 'month' or 'year' without quantity")
    return (unit in ("month", "year")), {unit + "s": qty}


def fill_missing_intervals(data, interval_str, start_ts, limit, key_name, end_ts=None):
    """
    data: list of dicts with 'ts' (timezone-aware or naive), 'value', 'count', 'key_name'
    interval_str: interval string per parse_interval
    start_ts: datetime or string in '%Y-%m-%d %H:%M:%S'
    limit: number of intervals to generate
    key_name: fallback name for empty intervals
    end_ts: optional end boundary - stops generating intervals after this time

    Fills gaps by stepping from start_ts for 'limit' intervals (or until end_ts).
    Normalizes timezone awareness so lookups match.
    """
    if not interval_str or not start_ts or not limit:
        return []

    # parse start_ts
    if isinstance(start_ts, str):
        start_ts = datetime.datetime.strptime(start_ts, "%Y-%m-%d %H:%M:%S")

    if end_ts and isinstance(end_ts, str):
        end_ts = datetime.datetime.strptime(end_ts, "%Y-%m-%d %H:%M:%S")

    # detect tzinfo from first data record (if any)
    tz = None

    if data:
        tz = getattr(data[0]["ts"], "tzinfo", None)

    if tz and start_ts.tzinfo is None:
        start_ts = start_ts.replace(tzinfo=tz)

    if end_ts:
        if tz and end_ts.tzinfo is None:
            end_ts = end_ts.replace(tzinfo=tz)
        elif not tz and end_ts.tzinfo is not None:
            end_ts = end_ts.replace(tzinfo=None)

    use_rd, delta_kwargs = parse_interval(interval_str)
    result = []

    # Build lookup by normalized timestamp (float seconds since epoch)
    def make_key(dt):
        # ensure dt is timezone-aware if tz is set
        if tz and dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        # drop tzinfo for consistent timestamp()
        return dt.timestamp()

    data_by_key = {make_key(rec["ts"]): rec for rec in data}

    current = start_ts
    last_known = None

    for _ in range(limit):
        if end_ts and current > end_ts:
            break

        key = make_key(current)
        record = data_by_key.get(key)

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
        # advance
        if use_rd:
            current = current + relativedelta(**delta_kwargs)  # pyright: ignore
        else:
            current = current + datetime.timedelta(**delta_kwargs)

    return result