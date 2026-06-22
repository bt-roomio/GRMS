from dataclasses import dataclass
from typing import Generic, TypeVar, cast

from rest_framework import serializers

T = TypeVar("T", bound="PaginationParams")


@dataclass
class PaginationParams:
    page: int
    size: int


class PaginationSerializer(serializers.Serializer, Generic[T]):
    params_class: type[T] | None = None

    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=50, min_value=1, max_value=500)

    @classmethod
    def parse(cls, query_params) -> T:
        s = cls(data=query_params)
        s.is_valid(raise_exception=True)
        params_class = cls.params_class or PaginationParams
        return cast(T, params_class(**s.validated_data))
