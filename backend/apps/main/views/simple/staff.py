from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from access_manager.models import Staff
from access_manager.serializers.staff import StaffQuickFilterParams
from core.utils.permission import check_perms
from core.utils.views import TenantCachedMixin


class StaffQuickListView(TenantCachedMixin, APIView):
    cache_key_prefix = "staffs"

    def get_data(self, tenant_id, **kwargs):
        return list(
            Staff.objects.quick_list(
                tenant_id=tenant_id,
                search_value=kwargs.get("search_value"),
            ).values("id", "first_name", "last_name")
        )

    @swagger_auto_schema(
        tags=["Main, Simple"],
        query_serializer=StaffQuickFilterParams(),
        responses={
            200: openapi.Response(
                description="Success",
                examples={"application/json": [{"id": "uuid", "first_name": "string", "last_name": "string"}]},
            )
        },
    )
    @check_perms(["users.view_user"])
    def get(self, request):
        params = StaffQuickFilterParams.check(request.GET)
        data = self.get_cached_data(str(request.user.tenant_id), **params)
        return Response(data)
