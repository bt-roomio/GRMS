import re
from datetime import timedelta

from dateutil.relativedelta import relativedelta


def parse_interval(interval_str):
    """
    Parse a string like '2 hours', '15 minutes', '1 day', 'month', or 'year'.
    Months and years must be singular (no quantities); others can have quantities.
    Returns: (use_relativedelta: bool, kwargs: dict)
    """
    # allow optional quantity for seconds-minutes-hours-days-weeks
    pattern = (
        r"^(?:(?P<qty>\d+)\s+)?" r"(?P<unit>second|seconds|minute|minutes|hour|hours|day|days|week|weeks|month|year)$"
    )
    match = re.match(pattern, interval_str)
    if not match:
        raise ValueError(f"Invalid interval: {interval_str}")
    qty = match.group("qty")
    unit = match.group("unit")

    unit_s = unit.rstrip("s")

    # months and year must be singular and no qty
    if unit_s in ("month", "year"):
        if qty is not None:
            raise ValueError(f"Interval '{interval_str}' invalid: use 'month' or 'year' without a quantity")
        return True, {unit_s + "s": 1}

    # for other units, default qty to 1 if missing
    qty = int(qty) if qty else 1
    delta_arg = {unit_s + "s": qty}
    # weeks still use timedelta
    use_rd = False
    return use_rd, delta_arg


def fill_missing_intervals(data, interval_str, start=None, end=None):
    """
    data: list of dicts with 'ts', 'value', 'count', etc.
    interval_str: string like '2 hours', '15 minutes', '1 day', 'month', or 'year'.
    start, end: optional datetime bounds
    """
    if not data:
        return []

    data = sorted(data, key=lambda x: x["ts"])
    use_rd, delta_kwargs = parse_interval(interval_str)

    curr = start or data[0]["ts"]
    last = end or data[-1]["ts"]

    filled = []
    idx = 0
    prev = None

    while curr <= last:
        if idx < len(data) and data[idx]["ts"] == curr:
            prev = data[idx]
            filled.append(prev)
            idx += 1
        else:
            filled.append(
                {
                    "ts": curr,
                    "value": prev["value"] if prev else 0.0,
                    "count": 0,
                    "key_name": prev["key_name"] if prev else None,
                }
            )
        if use_rd:
            curr = curr + relativedelta(**delta_kwargs)  # pyright:ignore
        else:
            curr = curr + timedelta(**delta_kwargs)

    return filled
