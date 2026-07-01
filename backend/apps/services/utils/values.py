VALUE_FIELDS = ("bool_v", "str_v", "long_v", "dbl_v", "json_v")


def get_non_null_value(row):
    """Return the first non-null typed value column of an AttributeKv/TsKvLatest
    ``.values()`` row, preserving its native JSON type. Local to the services API so
    the new endpoints do not depend on shuttle helpers."""
    if row:
        for field in VALUE_FIELDS:
            value = row.get(field)
            if value is not None:
                return value
    return None
