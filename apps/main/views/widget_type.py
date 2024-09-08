from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from main.models import WidgetType
from main.serializers.widget_type import WidgetTypeFilterParams, WidgetTypeSerializer
from main.swagger.widget_type import WidgetTypeDetailSwagger, WidgetTypeSwagger


class WidgetTypeListView(APIView):
    @swagger_auto_schema(responses=WidgetTypeSwagger, query_serializer=WidgetTypeFilterParams())
    def get(self, request):
        params = WidgetTypeFilterParams.check(request.GET)
        instance = WidgetType.objects.filter(tenant_id=request.user.tenant_id)
        serializer = WidgetTypeSerializer(instance, many=True)
        data = pagination(instance, serializer, params.get("page"), params.get("size"))
        return Response(data)

    @swagger_auto_schema(responses=WidgetTypeSwagger, request_body=WidgetTypeSerializer)
    def post(self, request):
        serializer = WidgetTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant=request.user.tenant)
        return Response(serializer.data, 201)


class WidgetTypeDetailView(APIView):
    @swagger_auto_schema(responses=WidgetTypeDetailSwagger)
    def get(self, request, pk):
        instance = get_object_or_404(WidgetType, id=pk)
        serializer = WidgetTypeSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(responses=WidgetTypeDetailSwagger, request_body=WidgetTypeSerializer)
    def put(self, request, pk):
        instance = get_object_or_404(WidgetType, id=pk)
        serializer = WidgetTypeSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(responses={})
    def delete(self, request, pk):
        instance = get_object_or_404(WidgetType, id=pk)
        instance.delete()
        return Response({}, 204)
