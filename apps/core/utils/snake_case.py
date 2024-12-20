import re


def camel_to_snake(camel_str):
    """
    Converts a camelCase string to snake_case.
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel_str).lower()


def snake_to_camel(snake_str):
    """
    Converts a snake_case string to camelCase.
    """
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def convert_keys(data, convert_func):
    """
    Recursively converts all dictionary keys using the provided conversion function.

    Args:
        data (dict or list): The data structure whose keys need conversion.
        convert_func (callable): The function to apply to keys (e.g., camel_to_snake or snake_to_camel).

    Returns:
        dict or list: A new data structure with converted keys.
    """
    if isinstance(data, dict):
        return {convert_func(key): convert_keys(value, convert_func) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_keys(item, convert_func) for item in data]
    else:
        return data


def convert_to_snake(data):
    return convert_keys(data, camel_to_snake)


def convert_to_camel(data):
    return convert_keys(data, snake_to_camel)
