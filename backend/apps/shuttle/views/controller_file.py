from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from shuttle.models import Controller
from shuttle.serializers.controller_file import ControllerLegacySerializer, ControllerParams, ControllerSerializer
from shuttle.swagger.controller_file import controller_file_swagger, controller_list_swagger


class ControllerFileListView(APIView):
    @controller_list_swagger()
    @check_perms(["shuttle.view_controller"])
    def get(self, request):
        params = ControllerParams.check(request.query_params)
        queryset = Controller.objects.list(  # ty: ignore
            tenant=request.user.tenant_id,
            sort_by=params.get("sort_by"),
            search_value=params.get("search_value"),
            file_type=params.get("file_type"),
        )
        serializer = ControllerSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))
        return Response(data)

    @controller_file_swagger()
    @check_perms(["shuttle.add_controllerfile"])
    def post(self, request):
        serializer = ControllerLegacySerializer(data=request.data, context={"tenant_id": request.user.tenant_id})
        serializer.is_valid(raise_exception=True)
        saved_data = serializer.save()
        return Response(saved_data)
