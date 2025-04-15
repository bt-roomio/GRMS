import json

from rest_framework import serializers


class DynamicField(serializers.Field):
    """
    A custom field that accepts multiple types: JSON (dict, list), string,
    boolean, integer, or float. If the input is a string, it will attempt to
    decode it as JSON. If that fails, it returns the string as is.
    """

    @staticmethod
    def convert_data(value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed
            except json.JSONDecodeError:
                return value
        return value

    def to_internal_value(self, data):
        return self.convert_data(data)

    def to_representation(self, value):
        return self.convert_data(value)
