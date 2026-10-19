from functools import lru_cache


@lru_cache(maxsize=1024)
def _get_field_type(value_type: type) -> str | None:
    """Cached type-to-field mapping to avoid repeated type checks"""
    if value_type is bool:
        return "bool_v"
    elif value_type is str:
        return "str_v"
    elif value_type is int:
        return "long_v"
    elif value_type is float:
        return "dbl_v"
    elif value_type in (dict, list):
        return "json_v"


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
