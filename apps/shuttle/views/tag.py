from rest_framework.response import Response
from rest_framework.views import APIView

from shuttle.consumers.aggregations.latest_telemetry import get_ts_kv_dict
from shuttle.models import AttributeKv, TsKvDictionary, TsKvLatest
from shuttle.serializers.tag import TagFilterPath, TagFilterParams
from shuttle.swagger.tag import tag_swagger
from shuttle.utils.get_non_null_field import get_non_null_field


class TagListView(APIView):
    @tag_swagger()
    def get(self, request, *args, **kwargs):
        path = TagFilterPath.check(kwargs)
        params = TagFilterParams.check(request.GET)
        if path.get("scope") != "LATEST_TELEMETRY":
            result = {"data": {}, "latestValues": {}}
            queryset = AttributeKv.objects.filter(
                entity_id=path.get("device_id"),
                attribute_type=path.get("scope"),
                attribute_key__in=params.get("tags"),
                entity__tenant_id=request.user.tenant_id,
            )
            for attribute in queryset:
                field, value = get_non_null_field(attribute)
                ts = attribute.last_update_ts
                result["data"][attribute.attribute_key] = [[ts, value]]
                result["latestValues"][attribute.attribute_key] = ts
        else:
            result = {"data": {}, "latestValues": {}}
            keys = TsKvDictionary.objects.get_key_ids(params.get("tags"))
            queryset = TsKvLatest.objects.filter(
                key__in=keys,
                entity_id=path.get("device_id"),
                entity__tenant_id=request.user.tenant_id,
            )
            for d in queryset:
                ts_kv_dict = get_ts_kv_dict(d.key)
                field, value = get_non_null_field(d)
                result["data"][ts_kv_dict.key] = [[d.ts, value]]
                result["latestValues"][ts_kv_dict.key] = d.ts

        return Response(result)
