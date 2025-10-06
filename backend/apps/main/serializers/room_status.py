from rest_framework import serializers


class RoomHistoryStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    last_24_hour = serializers.IntegerField()  # TODO: change after Presentation
    diff_previous_day = serializers.IntegerField()

class RoomLiveStatusSerializer(serializers.Serializer):
    available = serializers.IntegerField()
    checkedin = serializers.IntegerField()
    offline = serializers.IntegerField()
    dnd = serializers.IntegerField()
    mur = serializers.IntegerField()
    occupied = serializers.IntegerField()
    ac_on_off = serializers.IntegerField(source="ac-on-off")
