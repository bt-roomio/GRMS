from rest_framework import serializers


class RoomStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    last_24_hour = serializers.IntegerField()
    diff_previous_day = serializers.IntegerField()
