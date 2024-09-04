from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from main.models import Dashboard
from main.serializers.dashboard import DashboardFilterParams, DashboardSerializer
from main.swagger.dashboard import DashboardDetailSwagger, DashboardSwagger


class DashboardListView(APIView):
    @swagger_auto_schema(responses=DashboardSwagger, query_serializer=DashboardFilterParams())
    def get(self, request):
        params = DashboardFilterParams.check(request.GET)
        queryset = Dashboard.objects.filter(tenant_id=request.user.tenant_id)
        serializer = DashboardSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))
        return Response(data)

    @swagger_auto_schema(responses=DashboardSwagger, request_body=DashboardSerializer)
    def post(self, request):
        serializer = DashboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data, 201)


class DashboardDetailView(APIView):
    @swagger_auto_schema(responses=DashboardDetailSwagger)
    def get(self, request, pk):
        room_type = get_object_or_404(Dashboard, pk=pk, tenant=request.user.tenant)
        serializer = DashboardSerializer(room_type)
        return Response(serializer.data)

    @swagger_auto_schema(responses=DashboardDetailSwagger, request_body=DashboardSerializer)
    def put(self, request, pk):
        instance = get_object_or_404(Dashboard, id=pk)
        serializer = DashboardSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(responses={})
    def delete(self, request, pk):
        instance = get_object_or_404(Dashboard, id=pk)
        instance.delete()
        return Response({}, 204)
