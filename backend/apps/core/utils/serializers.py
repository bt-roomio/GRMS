from typing import Any, Dict, Optional, cast

from rest_framework.serializers import Serializer


class BaseSerializer(Serializer):
    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ValidatorSerializer(BaseSerializer, object):
    @classmethod
    def check(cls, data: Any, many: bool = False, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        serializer = cls(data=data, many=many, context=context or {})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        assert validated_data is not None, "Validated data should not be None after validation."
        return cast(Dict[str, Any], validated_data)
