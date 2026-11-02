from dataclasses import dataclass

from rest_framework import serializers

from core.serializers.pagination import PaginationParams, PaginationSerializer
from main.models import RoomType


class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = ("id", "title")


@dataclass
class RoomTypeFilterParams(PaginationParams):
    sort_by: str


class RoomTypeFilterSerializer(PaginationSerializer[RoomTypeFilterParams]):
    SORT_CHOICES = ("title", "-title")
    params_class = RoomTypeFilterParams

    sort_by = serializers.ChoiceField(choices=SORT_CHOICES, default="title")
