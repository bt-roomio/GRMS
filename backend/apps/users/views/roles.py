from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.permission import check_perms
from users.models import Role
from users.serializers.role import RoleSerializer, RoleSimpleSerializer
from users.swagger.roles import RolesSwagger, RoleDetailSwagger


class RolesListView(APIView):
    @swagger_auto_schema(operation_description="Getting all user roles.", responses=RolesSwagger)
    @check_perms(["users.view_role"])
    def get(self, request):
        instance = Role.objects.list(tenant=request.user.tenant, is_superuser=request.user.is_superuser)
        serializer = RoleSerializer(instance, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Creating a role for exactly tenant.",
        responses=RoleDetailSwagger,
        request_body=RoleSerializer,
    )
    @check_perms(["users.add_role"])
    def post(self, request):
        if Role.objects.filter(tenant=request.user.tenant, name=request.data.get("name")).exists():
            raise ValidationError({"non_field_errors": "The fields name, tenant must make a unique set."})
        is_superuser = request.user.is_superuser
        serializer = RoleSerializer(data=request.data, context={"is_superuser": is_superuser})
        serializer.is_valid(raise_exception=True)
        tenant_id = request.data.get("tenant") if is_superuser else request.user.tenant_id
        serializer.save(tenant_id=tenant_id)
        return Response(serializer.data, 201)


class RoleDetailView(APIView):
    @swagger_auto_schema(responses=RoleDetailSwagger)
    @check_perms(["users.view_role"])
    def get(self, request, pk):
        if request.user.is_superuser:
            instance = get_object_or_404(Role, pk=pk)
        else:
            instance = get_object_or_404(Role, pk=pk, tenant=request.user.tenant)
        serializer = RoleSimpleSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(responses=RoleDetailSwagger)
    @check_perms(["users.change_role"])
    def put(self, request, pk):
        if request.user.is_superuser:
            instance = get_object_or_404(Role, pk=pk)
        else:
            instance = get_object_or_404(Role, pk=pk, tenant=request.user.tenant)
        serializer = RoleSerializer(instance, data=request.data, context={"is_superuser": request.user.is_superuser})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(responses={})
    @check_perms(["users.delete_role"])
    def delete(self, request, pk):
        if request.user.is_superuser:
            instance = get_object_or_404(Role, pk=pk)
        else:
            instance = get_object_or_404(Role, pk=pk, tenant=request.user.tenant)
        instance.delete()
        return Response({}, 204)
