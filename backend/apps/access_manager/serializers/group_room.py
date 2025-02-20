from access_manager.models import GroupPublicSpace, GroupRoom

from rest_framework import serializers


class SimpleGroupRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupRoom
        fields = ("id", "group", "room")


class SimpleGroupPublicSpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupPublicSpace
        fields = ("id", "group", "public_space")
