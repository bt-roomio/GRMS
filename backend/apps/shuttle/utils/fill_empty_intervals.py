import re
from datetime import timedelta

from dateutil.relativedelta import relativedelta


def parse_interval(interval_str):
    """
    Parse a string like '2 hours', '15 minutes', '1 day', 'month', or 'year'.
    Months and years must be singular (no quantities); others can have quantities.
    Returns: (use_relativedelta: bool, kwargs: dict)
    """
    pattern = (
        r"^(?:(?P<qty>\d+)\s+)?" r"(?P<unit>second|seconds|minute|minutes|hour|hours|day|days|week|weeks|month|year)$"
    )
    match = re.match(pattern, interval_str)
    if not match:
        raise ValueError(f"Invalid interval: {interval_str}")
    qty = match.group("qty")
    unit = match.group("unit")

    unit_s = unit.rstrip("s")
    # months and year singular only
    if unit_s in ("month", "year"):
        if qty is not None:
            raise ValueError(f"Interval '{interval_str}' invalid: use 'month' or 'year' without a quantity")
        return True, {unit_s + "s": 1}

    qty = int(qty) if qty else 1
    return False, {unit_s + "s": qty}


def fill_missing_intervals(data, interval_str):
    """
    Fill missing time intervals between each pair of records in the original order.

    data: list of dicts with 'ts' datetime, 'value', 'count', etc.
    interval_str: e.g. '2 hours', '15 minutes', '1 day', 'month', or 'year'.
    Returns a new list of dicts, preserving original order with fillers.
    """
    if not data or not interval_str:
        return list(data)

    use_rd, delta_kwargs = parse_interval(interval_str)
    filled = []
    prev = None

    for record in data:
        if prev is None:
            # first record
            filled.append(record)
        else:
            # step from prev.ts until reaching current record.ts
            next_ts = prev["ts"] + (
                relativedelta(**delta_kwargs) if use_rd else timedelta(**delta_kwargs)  # pyright: ignore
            )
            while next_ts < record["ts"]:
                filled.append(
                    {
                        "ts": next_ts,
                        "value": prev["value"],
                        "count": 0,
                        "key_name": prev["key_name"],
                    }
                )
                next_ts = next_ts + (
                    relativedelta(**delta_kwargs) if use_rd else timedelta(**delta_kwargs)  # pyright: ignore
                )
            # then append actual record
            filled.append(record)
        prev = record

    return filled
