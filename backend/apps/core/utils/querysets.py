import json


def _cast_value(val):
    """Cast a TextField string back to its native Python type."""
    if val is None:
        return None
    if not isinstance(val, str):
        return val
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    try:
        return json.loads(val)
    except (json.JSONDecodeError, ValueError):
        return val
