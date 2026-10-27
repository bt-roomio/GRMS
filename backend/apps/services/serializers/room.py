from dataclasses import dataclass
from uuid import UUID

from rest_framework import serializers

from core.serializers.pagination import PaginationParams, PaginationSerializer
from main.models import Room


class RoomSerializer(serializers.ModelSerializer):
    type_id = serializers.UUIDField(read_only=True, allow_null=True)
    type_name = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Room
        fields = ("id", "number", "type_id", "type_name")


@dataclass
class RoomFilterParams(PaginationParams):
    sort_by: str
    room_type: UUID | None


class RoomFilterSerializer(PaginationSerializer[RoomFilterParams]):
    SORT_CHOICES = ("number", "-number")
    params_class = RoomFilterParams

    sort_by = serializers.ChoiceField(choices=SORT_CHOICES, default="number")
    room_type = serializers.UUIDField(default=None, help_text="Filter rooms by room type ID.")
