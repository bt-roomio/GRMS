from core.utils.pagination import pagination
from django.db.models import F
from drf_yasg.utils import swagger_auto_schema
from main.models import Dashboard, Tenant
from main.serializers.dashboard import DashboardFilterParams, DashboardSerializer, DashboardTypeSerializer
from main.swagger.dashboard import DashboardDetailSwagger, DashboardSwagger
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response


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
        instance = get_object_or_404(Dashboard, pk=pk, tenant=request.user.tenant)
        serializer = DashboardSerializer(instance)
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


class DashboardTypeView(APIView):
    @swagger_auto_schema(
        operation_description="Getting Dashboard by category **[main_dashboard, public_space_dashboard]**",
        query_serializer=DashboardTypeSerializer(),
        responses=DashboardDetailSwagger,
    )
    def get(self, request):
        """
        d == dashboard
        d_type == dashboard_type
        """
        params = DashboardTypeSerializer.check(request.GET)
        type_d = f"additional_info__general_settings__{params.get("type")}"
        criteria = {f"{type_d}__isnull": False, "id": request.user.tenant_id}

        has_d_type = Tenant.objects.filter(**criteria).annotate(d_type_pk=F(type_d)).values("d_type_pk").first()

        if not has_d_type:
            raise ValidationError({f"{params.get("type")}": ["Object does not exist in general_settings!"]})

        instance = get_object_or_404(Dashboard, pk=has_d_type.get("d_type_pk"), tenant=request.user.tenant)
        serializer = DashboardSerializer(instance)
        return Response(serializer.data)
