import time
from rest_framework.views import APIView, Response
from rest_framework.parsers import JSONParser

from shuttle.models import AttributeKv
from shuttle.serializers.attributes import AttributeKvParams


class AttributeListView(APIView):
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        params = AttributeKvParams(data=kwargs)
        params.is_valid(raise_exception=True)
        params_data = params.validated_data
        save_attributes(params_data, request.data)
        return Response({}, 201)


def save_attributes(params, data):
    for key, value in data.items():
        available_raw = {
            "bool_v": None,
            "str_v": None,
            "long_v": None,
            "dbl_v": None,
            "json_v": None,
        }
        if isinstance(value, bool):
            available_raw["bool_v"] = value
        elif isinstance(value, str):
            available_raw["str_v"] = value
        elif isinstance(value, int):
            available_raw["long_v"] = value
        elif isinstance(value, float):
            available_raw["dbl_v"] = value
        elif isinstance(value, dict) or isinstance(value, list):
            available_raw["json_v"] = value

        obj, _ = AttributeKv.objects.update_or_create(
            entity=params.get("deviceId"),
            attribute_type=params.get("scope"),
            attribute_key=key,
            defaults={"entity_type": "DEVICE", **available_raw, "last_update_ts": time.time()},
        )
