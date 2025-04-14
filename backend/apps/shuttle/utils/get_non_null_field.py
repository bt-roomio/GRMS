from typing import Any

from django.db.models import QuerySet

from shuttle.models import TsKv

fields_to_check = ["bool_v", "str_v", "long_v", "dbl_v", "json_v"]


def get_non_null_field(queryset):
    if queryset:
        for field in fields_to_check:
            value = getattr(queryset, field)

            if value is not None:
                return field, value

    return None, None


def get_non_null_column(data: dict):
    if data:
        for field in fields_to_check:
            value = data.get(field)

            if value is not None:
                return field, value

    return None, None


def filter_values(data: QuerySet[TsKv, dict[str, Any]]):
    for r in data:
        for field in fields_to_check:
            if r.get(field) is not None:
                r["value"] = r.get(field)
                r["type"] = field
            del r[field]

    return data
