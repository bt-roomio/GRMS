import json

from rest_framework import serializers


class DynamicField(serializers.Field):
    """
    A custom field that accepts multiple types: JSON (dict, list), string,
    boolean, integer, or float. If the input is a string, it will attempt to
    decode it as JSON. If that fails, it returns the string as is.
    """

    def to_internal_value(self, data):
        # If it's a string, try to decode it as JSON.
        if isinstance(data, str):
            try:
                # Attempt to load JSON from the string.
                parsed = json.loads(data)
                return parsed
            except json.JSONDecodeError:
                # If decoding fails, keep it as a string.
                return data
        # For non-string types, just return the data directly.
        return data

    def to_representation(self, value):
        # For output, simply return the value.
        return value
