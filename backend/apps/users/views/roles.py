from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.permission import check_perms
from users.models import Role
from users.serializers.role import RoleSerializer, RoleSimpleSerializer
from users.swagger.roles import RoleDetailSwagger, RolesSwagger
from users.utils.tenant_access import available_tenants_qs, is_unscoped_superuser, scoped_tenant_ids


def get_role_for(request, pk):
    """A chain admin is a superuser, so the scope has to be the chain, not the system."""
    if is_unscoped_superuser(request.user):
        return get_object_or_404(Role, pk=pk)
    return get_object_or_404(Role, pk=pk, tenant__in=available_tenants_qs(request.user))


def resolve_role_tenant_id(request):
    """
    The hotel a new role belongs to.

    An unpinned superuser may name any hotel; a chain admin only hotels of their
    chain; everyone else silently gets their own, as before. Ids are compared as
    strings so a malformed uuid becomes a 400 rather than a database error.
    """
    if not request.user.is_superuser:
        return request.user.tenant_id

    tenant_id = request.data.get("tenant")
    if is_unscoped_superuser(request.user):
        return tenant_id

    if str(tenant_id) not in scoped_tenant_ids(request.user):
        raise ValidationError({"tenant": "Tenant out of scope."})
    return tenant_id


class RolesListView(APIView):
    @swagger_auto_schema(tags=["Users, Role"], operation_description="Getting all user roles.", responses=RolesSwagger)
    @check_perms(["users.view_role"])
    def get(self, request):
        instance = Role.objects.list(
            tenants=available_tenants_qs(request.user),
            unscoped=is_unscoped_superuser(request.user),
        )
        serializer = RoleSerializer(instance, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=["Users, Role"],
        operation_description="Creating a role for exactly tenant.",
        responses=RoleDetailSwagger,
        request_body=RoleSerializer,
    )
    @check_perms(["users.add_role"])
    def post(self, request):
        is_superuser = request.user.is_superuser
        tenant_id = resolve_role_tenant_id(request)

        if Role.objects.filter(tenant_id=tenant_id, name=request.data.get("name")).exists():
            raise ValidationError({"non_field_errors": "The fields name, tenant must make a unique set."})

        serializer = RoleSerializer(data=request.data, context={"is_superuser": is_superuser})
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=tenant_id)
        return Response(serializer.data, 201)


class RoleDetailView(APIView):
    @swagger_auto_schema(tags=["Users, Role"], responses=RoleDetailSwagger)
    @check_perms(["users.view_role"])
    def get(self, request, pk):
        return Response(RoleSimpleSerializer(get_role_for(request, pk)).data)

    @swagger_auto_schema(tags=["Users, Role"], responses=RoleDetailSwagger)
    @check_perms(["users.change_role"])
    def put(self, request, pk):
        instance = get_role_for(request, pk)
        serializer = RoleSerializer(instance, data=request.data, context={"is_superuser": request.user.is_superuser})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(tags=["Users, Role"], responses={})
    @check_perms(["users.delete_role"])
    def delete(self, request, pk):
        get_role_for(request, pk).delete()
        return Response({}, 204)
