from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from main.models import GlobalSettingsTemplate, Room
from main.serializers.global_settings_template import (
    ApplyGlobalSettingsTemplateSerializer,
    GlobalSettingsRoomFilterParams,
    GlobalSettingsRoomFilterParamsSwagger,
    GlobalSettingsRoomSerializer,
    GlobalSettingsTemplateFilterParams,
    GlobalSettingsTemplateSerializer,
)
from main.services.global_settings import apply_template
from main.swagger.global_settings_template import (
    ApplyGlobalSettingsTemplateSwagger,
    GlobalSettingsRoomListSwagger,
    GlobalSettingsTemplateCreateSwagger,
    GlobalSettingsTemplateDetailSwagger,
    GlobalSettingsTemplateListSwagger,
)

TAGS = ["Main, Global Settings"]


class GlobalSettingsTemplateListView(APIView):
    @swagger_auto_schema(
        tags=TAGS,
        responses=GlobalSettingsTemplateListSwagger,
        query_serializer=GlobalSettingsTemplateFilterParams,
        security=[{"Bearer": []}],
        operation_description="Returns global settings templates.",
    )
    @check_perms(["main.view_globalsettingstemplate"])
    def get(self, request):
        params = GlobalSettingsTemplateFilterParams.check(request.query_params)
        queryset = GlobalSettingsTemplate.objects.filter(tenant=request.user.tenant).list(
            sort_by=params.get("sort_by"),
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
        )
        serializer = GlobalSettingsTemplateSerializer(queryset, many=True)
        return Response(pagination(queryset, serializer, params.get("page"), params.get("size")))

    @swagger_auto_schema(
        tags=TAGS,
        request_body=GlobalSettingsTemplateSerializer,
        responses=GlobalSettingsTemplateCreateSwagger,
        security=[{"Bearer": []}],
        operation_description="Creates a global settings template.",
    )
    @check_perms(["main.add_globalsettingstemplate"])
    def post(self, request):
        serializer = GlobalSettingsTemplateSerializer(data=request.data, context={"tenant": request.user.tenant})
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant=request.user.tenant, created_by=request.user, updated_by=request.user)
        return Response(serializer.data, 201)


class GlobalSettingsTemplateDetailView(APIView):
    @swagger_auto_schema(
        tags=TAGS,
        responses=GlobalSettingsTemplateDetailSwagger,
        security=[{"Bearer": []}],
        operation_description="Returns a single global settings template.",
    )
    @check_perms(["main.view_globalsettingstemplate"])
    def get(self, request, pk):
        instance = get_object_or_404(GlobalSettingsTemplate, pk=pk, tenant=request.user.tenant)
        return Response(GlobalSettingsTemplateSerializer(instance).data)

    @swagger_auto_schema(
        tags=TAGS,
        request_body=GlobalSettingsTemplateSerializer,
        responses=GlobalSettingsTemplateDetailSwagger,
        security=[{"Bearer": []}],
        operation_description="Updates a global settings template; `config` may be omitted to keep the current one.",
    )
    @check_perms(["main.change_globalsettingstemplate"])
    def put(self, request, pk):
        instance = get_object_or_404(GlobalSettingsTemplate, pk=pk, tenant=request.user.tenant)
        serializer = GlobalSettingsTemplateSerializer(
            instance, data=request.data, context={"tenant": request.user.tenant}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=TAGS,
        responses={204: "Deleted", 404: "Global settings template not found"},
        security=[{"Bearer": []}],
        operation_description="Deletes a global settings template.",
    )
    @check_perms(["main.delete_globalsettingstemplate"])
    def delete(self, request, pk):
        get_object_or_404(GlobalSettingsTemplate, pk=pk, tenant=request.user.tenant).delete()
        return Response({}, 204)


class GlobalSettingsRoomListView(APIView):
    @swagger_auto_schema(
        tags=TAGS,
        query_serializer=GlobalSettingsRoomFilterParamsSwagger,
        responses=GlobalSettingsRoomListSwagger,
        security=[{"Bearer": []}],
        operation_description=(
            "Returns the tenant's active rooms that have an active device, with their first device and the template applied to it "
            "(SERVER_SCOPE `template_id`): `status` is `up_to_date`, `outdated` (the template config changed "
            "after it was applied) or `deleted` (the template no longer exists, `name` is null). "
            "Filters: `room_types=id1,id2` and `blocks=<block>:<floor>,<floor>`, repeated per rule "
            "(e.g. `blocks=1:1,2,3&blocks=2:5`); a block without floors selects the whole block, "
            "`blocks=:1,2` selects floors 1 and 2 in every block. `blocks` rules are combined with OR, "
            "`room_types` and `blocks` with AND. `search_field` (`number`, `floor`, `block`, `room_type`, `device`) with "
            "`search_value` is a case-insensitive substring search, the device is the one shown in the row."
        ),
    )
    @check_perms(["main.view_room", "main.view_globalsettingstemplate"])
    def get(self, request):
        params = GlobalSettingsRoomFilterParams.check(request.query_params)
        rows = list(
            Room.objects.global_settings(
                tenant=request.user.tenant,
                room_types=params.get("room_types"),
                blocks=params.get("blocks"),
                search_field=params.get("search_field"),
                search_value=params.get("search_value"),
            )
        )
        templates = GlobalSettingsRoomSerializer.templates_of_rows(rows, request.user.tenant)
        return Response(GlobalSettingsRoomSerializer(rows, many=True, context={"templates": templates}).data)


class ApplyGlobalSettingsTemplateView(APIView):
    @swagger_auto_schema(
        tags=TAGS,
        request_body=ApplyGlobalSettingsTemplateSerializer,
        responses=ApplyGlobalSettingsTemplateSwagger,
        security=[{"Bearer": []}],
        operation_description=(
            "Applies a global settings template to the active devices of the given rooms: writes the template "
            "`config` to SHARED_SCOPE attributes, the `template_id` to SERVER_SCOPE and pushes the shared "
            "attributes to the devices (the device response is not awaited)."
        ),
    )
    @check_perms(["main.view_globalsettingstemplate", "shuttle.add_attributerpc"])
    def post(self, request):
        params = ApplyGlobalSettingsTemplateSerializer.check(request.data, context={"tenant": request.user.tenant})
        devices = apply_template(params["template_id"], params["room_ids"])
        return Response({"devices": devices})
