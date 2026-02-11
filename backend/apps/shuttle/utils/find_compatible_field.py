from functools import lru_cache


@lru_cache(maxsize=1024)
def _get_field_type(value_type: type) -> str:
    """Cached type-to-field mapping to avoid repeated type checks"""
    if value_type == bool:
        return "bool_v"
    elif value_type == str:
        return "str_v"
    elif value_type == int:
        return "long_v"
    elif value_type == float:
        return "dbl_v"
    elif value_type in (dict, list):
        return "json_v"
    return None


def find_compatible_field(data):
    """
    Map data fields to database column types.
    Optimized with cached type lookups for better performance.
    """
    available_raw = {}

    for key, value in data.items():
        value_type = type(value)
        field = _get_field_type(value_type)

        if field:
            available_raw[key] = field, value
        elif isinstance(value, dict) or isinstance(value, list):
            # Fallback for complex types not in cache
            available_raw[key] = "json_v", value

    return available_raw
