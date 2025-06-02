from access_manager.models import Group, GroupPublicSpace, GroupRoom, TypeChoices
from access_manager.serializers.group_room import SimpleGroupPublicSpaceSerializer, SimpleGroupRoomSerializer
from django.db.models import Q

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import PublicSpace, Room
from users.serializers.user import SimpleUserSerializer


class TypeChoiceField(serializers.Field):
    """
    A read/write field that:
      - on input: accepts the enum *name* ("ENGINEERING") and converts it to its integer (3)
      - on output: takes the integer stored in the model and returns the enum name ("ENGINEERING").
    """

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError(
                f"Invalid type for group_type. Expected string choice, got {type(data).__name__}."
            )

        try:
            return TypeChoices[data].value
        except KeyError:
            valid_names = ", ".join([choice.name for choice in TypeChoices])
            raise serializers.ValidationError(f'"{data}" is not a valid choice. ' f"Valid options are: {valid_names}.")

    def to_representation(self, value):
        try:
            return TypeChoices(value).name
        except ValueError:
            return value


class SimpleGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ("id", "name")


class GroupSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(default=True, read_only=True)
    created_by = SimpleUserSerializer(read_only=True)
    rooms_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Room.objects.all(), write_only=True)
    rooms = SimpleGroupRoomSerializer(source="group_room", read_only=True, many=True)
    public_spaces_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=PublicSpace.objects.all(), write_only=True
    )
    public_spaces = SimpleGroupPublicSpaceSerializer(source="group_public_space", read_only=True, many=True)
    group_type = TypeChoiceField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["count_staff"] = instance.count_staff if hasattr(instance, "count_staff") else 0
        return data

    def create(self, validated_data):
        rooms = validated_data.pop("rooms_ids")
        public_spaces = validated_data.pop("public_spaces_ids")

        instance = super().create(validated_data)

        for room in rooms:
            GroupRoom.objects.create(group=instance, room=room)

        for public_space in public_spaces:
            GroupPublicSpace.objects.create(group=instance, public_space=public_space)

        return instance

    def update(self, instance, validated_data):
        rooms = validated_data.pop("rooms_ids", None) if validated_data.get("rooms_ids") else []
        public_spaces = validated_data.pop("public_spaces_ids", None) if validated_data.get("public_spaces_ids") else []
        instance = super().update(instance, validated_data)

        instance.group_room.filter(~Q(room__in=rooms)).delete()
        for room in rooms:
            GroupRoom.objects.get_or_create(group=instance, room=room)

        instance.group_public_space.filter(~Q(public_space__in=public_spaces)).delete()
        for public_space in public_spaces:
            GroupPublicSpace.objects.get_or_create(group=instance, public_space=public_space)

        return instance

    class Meta:
        model = Group
        fields = (
            "id",
            "created_at",
            "created_by",
            "name",
            "group_type",
            "tenant",
            "rooms_ids",
            "rooms",
            "public_spaces_ids",
            "public_spaces",
            "week_days",
            "start_time",
            "end_time",
            "expiry_date",
            "is_active",
            "additional_info",
        )


class GroupFilterParams(ValidatorSerializer):
    SORT_FIELDS = (
        "name",
        "-name",
        "start_time",
        "-start_time",
        "end_time",
        "-end_time",
        "expiry_date",
        "-expiry_date",
        "created_by",
        "-created_by",
    )

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("name", "expiry_data"), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
