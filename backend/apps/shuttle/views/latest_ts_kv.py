from django.shortcuts import get_list_or_404

from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from main.models import Device
from services.utils.const import HOTEZA
from shuttle.models import TsKvLatest
from shuttle.serializers.ts_kv_latest import TsKvLatestIntegrationFilterParams, TsKvLatestIntegrationSerializer
from shuttle.utils.permissions import WhiteListOrIsAuthenticated


class LatestTsKvListView(APIView):
    permission_classes = (WhiteListOrIsAuthenticated,)

    @swagger_auto_schema(tags=["Shuttle, TsKv"])
    @check_perms(["shuttle.view_tskvlatest"])
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
            result["tenant__integration__integrator"] = HOTEZA
            result["tenant__integration__hotel_id"] = kwargs.get("hotel_id")
            result["tenant__integration__enable"] = True
            result["tenant__integration__is_active"] = True
            result["room__number"] = kwargs.get("room_number")
            return result
        return result
