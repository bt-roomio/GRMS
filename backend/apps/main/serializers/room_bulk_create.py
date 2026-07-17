from rest_framework import serializers


class RoomNumberValidator(serializers.Serializer):
    number = serializers.CharField(required=True)
    floor = serializers.CharField(required=True)
    block = serializers.CharField(required=True)
