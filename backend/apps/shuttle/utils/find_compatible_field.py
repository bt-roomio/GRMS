def find_compatible_field(data):
    available_raw = {}

    for key, value in data.items():
        if isinstance(value, bool):
            available_raw[key] = "bool_v", value
        elif isinstance(value, str):
            available_raw[key] = "str_v", value
        elif isinstance(value, int):
            available_raw[key] = "long_v", value
        elif isinstance(value, float):
            available_raw[key] = "dbl_v", value
        elif isinstance(value, dict) or isinstance(value, list):
            available_raw[key] = "json_v", value

    return available_raw
