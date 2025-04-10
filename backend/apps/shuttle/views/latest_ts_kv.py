from django.shortcuts import get_list_or_404

from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from main.models import Device
from shuttle.models import TsKvLatest
from shuttle.serializers.ts_kv_latest import TsKvLatestIntegrationFilterParams, TsKvLatestIntegrationSerializer
from shuttle.utils.permissions import WhiteListOrIsAuthenticated


class LatestTsKvListView(APIView):
    permission_classes = (WhiteListOrIsAuthenticated,)

    @swagger_auto_schema(tags=["Shuttle, TsKv"])
    def get(self, request, **kwargs):
        kwargs = self.make_kwargs(**kwargs)
        device = get_list_or_404(Device, **kwargs)[0]
        params = TsKvLatestIntegrationFilterParams.check(request.query_params)
        queryset = TsKvLatest.objects.get_entity(device).get_by_keys(params.get("keys"))  # pyright: ignore
        serializer = TsKvLatestIntegrationSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size", 15))
        return Response(data)

    def make_kwargs(self, **kwargs):
        result = {}
        if kwargs.get("tenant_id") and kwargs.get("room_number"):
            result["tenant_id"] = kwargs.get("tenant_id")
            result["room__number"] = kwargs.get("room_number")
            return result
        elif kwargs.get("hotel_id") and kwargs.get("room_number"):
            result["tenant__additional_info__integration_settings__hoteza__hotel_id"] = kwargs.get("hotel_id")
            result["room__number"] = kwargs.get("room_number")
            return result
        return result
