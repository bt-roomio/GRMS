from dataclasses import dataclass

from rest_framework import serializers

from core.serializers.pagination import PaginationParams, PaginationSerializer
from main.models import Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ("id", "number")


@dataclass
class RoomFilterParams(PaginationParams):
    sort_by: str


class RoomFilterSerializer(PaginationSerializer[RoomFilterParams]):
    SORT_CHOICES = ["number", "-number"]
    params_class = RoomFilterParams

    sort_by = serializers.ChoiceField(choices=SORT_CHOICES, default="number")
