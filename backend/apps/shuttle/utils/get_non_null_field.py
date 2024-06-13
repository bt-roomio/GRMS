def get_non_null_field(queryset):
    if queryset:
        fields_to_check = ["bool_v", "str_v", "long_v", "dbl_v", "json_v"]
        for field in fields_to_check:
            value = getattr(queryset, field)

            if value is not None:
                return field, value

    return None, None
