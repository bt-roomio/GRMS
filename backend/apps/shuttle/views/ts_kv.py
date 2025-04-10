from django.db.models import Q

from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Device
from shuttle.models import TsKv
from shuttle.serializers.ts_kv import TsKvFilterParams, TsKvFilterPath
from shuttle.utils.permissions import WhiteListOrIsAuthenticated


class TsKvListView(APIView):
    permission_classes = (WhiteListOrIsAuthenticated,)

    @swagger_auto_schema(tags=["Shuttle, TsKv"])
    def get(self, request, **kwargs):
        path = TsKvFilterPath.check(kwargs)
        device = Device.objects.filter(
            Q(id=path.get("entity_id"))  # pyright: ignore
            | Q(Q(tenant_id=path.get("tenant_id")) & Q(room_id=path.get("room_id")))  # pyright: ignore
        ).first()
        if not device:
            return Response({"detail": "Not found device."}, 404)

        params = TsKvFilterParams.check(request.GET)
        queryset, _ = TsKv.objects.by_device(device).get_history(**params)  # pyright: ignore
        return Response(queryset)
