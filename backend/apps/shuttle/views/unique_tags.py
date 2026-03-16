from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from shuttle.models import AttributeKv, TsKvLatest
from shuttle.serializers.unique_tags import UniqueTagsFilterParams


class UniqueTagsView(APIView):
    @swagger_auto_schema(
        tags=["Shuttle, Tags"], query_serializer=UniqueTagsFilterParams, responses={200: "A list of unique tags"}
    )
    @check_perms(["shuttle.view_tskvlatest"])
    def get(self, request):
        params = UniqueTagsFilterParams.check(request.query_params)
        tenant_id = request.user.tenant_id

        if params["tag_type"] == "telemetry":
            keys = TsKvLatest.objects.unique_keys_by_tenant(tenant_id)
        else:
            keys = AttributeKv.objects.unique_keys_by_tenant(tenant_id, params["attribute_scope"])

        page = params["page"]
        size = params["size"]
        offset = (page - 1) * size
        return Response({"count": keys.count(), "results": list(keys[offset : offset + size])})
