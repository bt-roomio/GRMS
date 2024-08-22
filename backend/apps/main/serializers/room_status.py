from rest_framework import serializers


class RoomStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()
