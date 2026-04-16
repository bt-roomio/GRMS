from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import PublicSpace, RoomType, RoomTypePublicSpaces
from main.serializers.dashboard import SimpleDashboardSerializer
from main.serializers.public_space import SimplePublicSpaceSerializer


class RoomTypeSerializer(serializers.ModelSerializer):
    public_spaces_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=PublicSpace.objects.all(), write_only=True, required=False
    )
    public_spaces = SimplePublicSpaceSerializer(many=True, read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["dashboard"] = SimpleDashboardSerializer(instance.dashboard).data if instance.dashboard else None

        if hasattr(instance, "prefetched_public_spaces"):
            public_spaces = instance.prefetched_public_spaces
            data["public_spaces"] = SimplePublicSpaceSerializer(public_spaces, many=True).data
        else:
            public_spaces = PublicSpace.objects.filter(room_type_public_spaces__room_type=instance)
            data["public_spaces"] = SimplePublicSpaceSerializer(public_spaces, many=True).data

        return data

    def create(self, validated_data):
        public_spaces_ids = validated_data.pop("public_spaces_ids", [])
        instance = super().create(validated_data)

        if public_spaces_ids:
            for public_space_id in public_spaces_ids:
                RoomTypePublicSpaces.objects.create(room_type=instance, public_space=public_space_id)

        return instance

    def update(self, instance, validated_data):
        public_spaces_ids = validated_data.pop("public_spaces_ids", None)
        instance = super().update(instance, validated_data)

        if public_spaces_ids is not None:
            RoomTypePublicSpaces.objects.filter(room_type=instance).delete()

            for public_space_id in public_spaces_ids:
                RoomTypePublicSpaces.objects.create(room_type=instance, public_space=public_space_id)

        return instance

    class Meta:
        model = RoomType
        fields = (
            "id",
            "title",
            "check_in_out_address",
            "check_in_value",
            "check_out_value",
            "dashboard",
            "tenant",
            "public_spaces_ids",
            "public_spaces",
        )


class RoomTypeFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("title",), required=False)
    search_value = serializers.CharField(required=False)


class RoomTypeQuickFilterParams(RoomTypeFilterParams):
    page = None
    size = None
    search_field = None
