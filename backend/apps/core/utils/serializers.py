from typing import Any, Dict, Optional, cast

from rest_framework import serializers
from rest_framework.generics import CreateAPIView
from rest_framework.serializers import Serializer
from rest_framework.utils.serializer_helpers import ReturnDict

from core.utils.perform_request import with_tenant


class BaseSerializer(Serializer):
    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ValidatorSerializer(BaseSerializer, object):
    # TODO: We can use generics for type hints
    @classmethod
    def check(cls, data: Any, many: bool = False, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        serializer = cls(data=data, many=many, context=context or {})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        assert validated_data is not None, "Validated data should not be None after validation."
        return cast(Dict[str, Any], validated_data)


class BaseCreateAPIView(CreateAPIView):
    def get_serializer(self, *args, **kwargs):
        # Only inject tenant data for write operations
        if self.request.method in ["POST", "PUT", "PATCH"]:
            tenant_data = with_tenant(self.request)  # This should return a dict of initial data
            if "data" in kwargs:
                # If data is already provided, merge it with tenant_data.
                data = kwargs["data"].copy()  # ensure it's mutable
                data.update(tenant_data)
                kwargs["data"] = data
            else:
                kwargs["data"] = tenant_data
        return super().get_serializer(*args, **kwargs)


class MillisecondDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        return int(value.timestamp() * 1000)


def dict_of_lists(data: ReturnDict) -> list:
    return [{k: v for k, v in dict(data).items()}]
