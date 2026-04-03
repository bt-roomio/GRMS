from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from core.utils.views import TenantCachedMixin
from main.models import Device
from main.serializers.device import DeviceQuickFilterParams


class DeviceQuickListView(TenantCachedMixin, APIView):
    cache_key_prefix = "devices"

    def get_data(self, tenant_id, **kwargs):
        return list(
            Device.objects.quick_list(
                tenant=tenant_id,
                search_value=kwargs.get("search_value"),
                device_profile=kwargs.get("device_profile"),
            ).values("id", "name", "label")
        )

    @swagger_auto_schema(
        tags=["Main, Simple, Device"],
        query_serializer=DeviceQuickFilterParams(),
        responses={
            200: openapi.Response(
                description="Success",
                examples={"application/json": [{"id": "uuid", "name": "string", "label": "string"}]},
            )
        },
    )
    @check_perms(["main.view_device"])
    def get(self, request):
        params = DeviceQuickFilterParams.check(request.GET)
        data = self.get_data(str(request.user.tenant_id), **params)
        return Response(data)
