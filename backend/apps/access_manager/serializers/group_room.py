from rest_framework import serializers

from access_manager.models import GroupPublicSpace, GroupRoom


class SimpleGroupRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupRoom
        fields = ("id", "group", "room")


class SimpleGroupPublicSpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupPublicSpace
        fields = ("id", "group", "public_space")
