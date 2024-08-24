import time

from rest_framework.parsers import JSONParser
from rest_framework.views import APIView, Response

from shuttle.models import AttributeKv
from shuttle.serializers.attributes import AttributeKvParams
from shuttle.utils.find_compatible_field import find_compatible_field


class AttributeListView(APIView):
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        params = AttributeKvParams(data=kwargs)
        params.is_valid(raise_exception=True)
        params_data = params.validated_data
        available_fields = find_compatible_field(request.data)

        for key, item in available_fields.items():
            fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
            field = item[0]
            value = item[1]
            fields[field] = value

            attribute_kv, _ = AttributeKv.objects.update_or_create(
                entity=params_data.get("deviceId"),
                attribute_type=params_data.get("scope"),
                attribute_key=key,
                defaults={"entity_type": "DEVICE", **fields, "last_update_ts": time.time()},
            )
        return Response({}, 201)
