from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    def get_first_non_none(self, *values):
        for value in values:
            if value is not None:
                return value
        return None
