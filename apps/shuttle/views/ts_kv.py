from rest_framework.response import Response
from rest_framework.views import APIView
from shuttle.models import TsKv
from shuttle.serializers.ts_kv import TsKvFilterParams, TsKvFilterPath


class TsKvListView(APIView):
    def get(self, request, *args, **kwargs):
        path = TsKvFilterPath.check(kwargs)
        params = TsKvFilterParams.check(request.GET)
        queryset = TsKv.objects.get_entity_ts_kv(path.get("entity_id")).get_history(**params)
        return Response(queryset)
