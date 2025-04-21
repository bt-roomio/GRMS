from drf_yasg.utils import swagger_auto_schema

from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from main.models import WidgetType
from main.serializers.widget_type import WidgetTypeFilterParams, WidgetTypeSerializer
from main.swagger.widget_type import WidgetTypeDetailSwagger, WidgetTypeSwagger
from core.utils.permission import check_perms

class WidgetTypeListView(APIView):
    @swagger_auto_schema(
        tags=["Main, WidgetType"], responses=WidgetTypeSwagger, query_serializer=WidgetTypeFilterParams()
    )
    @check_perms(["main.view_widgettype"])
    def get(self, request):
        params = WidgetTypeFilterParams.check(request.GET)
        instance = WidgetType.objects.all()
        serializer = WidgetTypeSerializer(instance, many=True)
        data = pagination(instance, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)

    @swagger_auto_schema(tags=["Main, WidgetType"], responses=WidgetTypeSwagger, request_body=WidgetTypeSerializer)
    @check_perms(["main.add_widgettype"])
    def post(self, request):
        serializer = WidgetTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant=request.user.tenant)
        return Response(serializer.data, 201)


class WidgetTypeDetailView(APIView):
    @swagger_auto_schema(tags=["Main, WidgetType"], responses=WidgetTypeDetailSwagger)
    @check_perms(["main.view_widgettype"])
    def get(self, request, pk):
        instance = get_object_or_404(WidgetType, id=pk)
        serializer = WidgetTypeSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=["Main, WidgetType"], responses=WidgetTypeDetailSwagger, request_body=WidgetTypeSerializer
    )
    @check_perms(["main.change_widgettype"])
    def put(self, request, pk):
        instance = get_object_or_404(WidgetType, id=pk)
        serializer = WidgetTypeSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(tags=["Main, WidgetType"], responses={})
    @check_perms(["main.delete_widgettype"])
    def delete(self, request, pk):
        instance = get_object_or_404(WidgetType, id=pk)
        instance.delete()
        return Response({}, 204)
