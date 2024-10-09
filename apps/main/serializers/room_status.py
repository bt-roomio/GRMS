from rest_framework import serializers


class RoomHistoryStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    last_24_hour = serializers.IntegerField()  # TODO: change after Presentation
    diff_previous_day = serializers.IntegerField()
