from admin_panel.swagger.tenant_groups import (
    AdminTenantGroupCreateSwagger,
    AdminTenantGroupDetailSwagger,
    AdminTenantGroupListSwagger,
)
from admin_panel.utils.scope import scoped_groups

from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import IsSuperUser
from main.models import TenantGroup
from main.serializers.tenant_group import (
    CreateTenantGroupSerializer,
    TenantGroupFilterParams,
    TenantGroupSerializer,
    UpdateTenantGroupSerializer,
)
from main.services.tenant_provisioning import dissolve_tenant_group
from users.models import User


class AdminTenantGroupListView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminTenantGroupListSwagger,
        query_serializer=TenantGroupFilterParams,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Returns all hotel chains.",
    )
    def get(self, request):
        params = TenantGroupFilterParams.check(request.query_params)
        queryset = scoped_groups(request).list(
            sort_by=params.get("sort_by"),
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
        )
        serializer = TenantGroupSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))
        return Response(data)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        request_body=CreateTenantGroupSerializer,
        responses=AdminTenantGroupCreateSwagger,
        security=[{"Bearer": []}],
        operation_description=(
            "**Superuser only.** Creates a hotel chain together with its administrator "
            "— a superuser pinned to the chain, who then manages only its hotels."
        ),
    )
    def post(self, request):
        if request.user.tenant_group_id:
            raise PermissionDenied("A chain admin cannot create another chain.")
        serializer = CreateTenantGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        return Response(TenantGroupSerializer(group).data, 201)


class AdminTenantGroupDetailView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminTenantGroupDetailSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Returns a single hotel chain.",
    )
    def get(self, request, group_id):
        group = get_object_or_404(scoped_groups(request).count_tenants(), pk=group_id)
        user = User.objects.filter(tenant_group=group, is_active=True, is_superuser=True).first()
        return Response(TenantGroupSerializer(group, context={"user": user}).data)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        request_body=UpdateTenantGroupSerializer,
        responses=AdminTenantGroupDetailSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Updates a hotel chain.",
    )
    def put(self, request, group_id):
        group = get_object_or_404(scoped_groups(request).count_tenants(), pk=group_id)
        serializer = UpdateTenantGroupSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user = User.objects.filter(tenant_group=group, is_active=True, is_superuser=True).first()
        return Response(TenantGroupSerializer(group, context={"user": user}).data)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses={204: "Deleted", 404: "Tenant group not found"},
        security=[{"Bearer": []}],
        operation_description=(
            "**Superuser only.** Deletes a chain. Its hotels survive and become standalone; "
            "its admins are deactivated so that none of them is left as an unpinned superuser."
        ),
    )
    def delete(self, request, group_id):
        if request.user.tenant_group_id:
            raise PermissionDenied("A chain admin cannot delete their own chain.")
        dissolve_tenant_group(get_object_or_404(TenantGroup, pk=group_id))
        return Response({}, 204)
