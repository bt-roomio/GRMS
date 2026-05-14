def parse_key_count(value):
    if value is None:
        return 1
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1
