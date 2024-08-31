from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.permission import IsTenantAndSysAdmin, check_perms
from users.models import Role
from users.serializers.group import RoleSerializer, GroupSimpleSerializer
from users.swagger.groups import GroupsSwagger, GroupDetailSwagger


class GroupsListView(APIView):
    @swagger_auto_schema(operation_description="Getting all user groups.", responses=GroupsSwagger)
    @check_perms(["users.view_role"])
    def get(self, request):
        instance = Role.objects.list(tenant=request.user.tenant, is_superuser=None)
        serializer = RoleSerializer(instance, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Creating a group for exactly tenant.",
        responses=GroupDetailSwagger,
        request_body=RoleSerializer,
    )
    @check_perms(["users.add_role"])
    def post(self, request):
        if Role.objects.filter(tenant=request.user.tenant, name=request.data.get("name")).exists():
            raise ValidationError({"non_field_errors": "The fields name, tenant must make a unique set."})

        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant=request.user.tenant)
        return Response(serializer.data, 201)


class GroupDetailView(APIView):
    permission_classes = [IsTenantAndSysAdmin]

    @swagger_auto_schema(responses=GroupDetailSwagger)
    @check_perms(["users.view_role"])
    def get(self, request, pk):
        group = get_object_or_404(Role, pk=pk, tenant=request.user.tenant)
        serializer = GroupSimpleSerializer(group)
        return Response(serializer.data)

    @swagger_auto_schema(responses=GroupDetailSwagger)
    @check_perms(["users.change_role"])
    def put(self, request, pk):
        instance = get_object_or_404(Role, pk=pk, tenant=request.user.tenant)
        serializer = RoleSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(responses={})
    @check_perms(["users.delete_role"])
    def delete(self, request, pk):
        group = get_object_or_404(Role, pk=pk, tenant=request.user.tenant)
        group.delete()
        return Response({}, 204)
