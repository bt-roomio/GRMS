from django.contrib.auth.models import Group
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.permission import check_for_tenant
from users.models import User
from users.serializers.group import GroupSerializer
from users.swagger.groups import GroupsSwagger, GroupDetailSwagger


class GroupsListView(APIView):
    @swagger_auto_schema(
        operation_description="Getting all groups for this tenant that you are logged in as a user.",
        responses=GroupsSwagger,
    )
    @check_for_tenant
    def get(self, request):
        users = User.objects.filter(tenant_id=request.user.tenant_id)
        instance = Group.objects.prefetch_related("permissions").filter(user__in=users).distinct("id")
        serializer = GroupSerializer(instance, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Creating a group for exactly tenant.",
        responses=GroupDetailSwagger,
        request_body=GroupSerializer,
    )
    @check_for_tenant
    def post(self, request):
        serializer = GroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, 201)


class GroupDetailView(APIView):
    @swagger_auto_schema(responses=GroupDetailSwagger)
    @check_for_tenant
    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        serializer = GroupSerializer(group)
        return Response(serializer.data)

    @swagger_auto_schema(responses=GroupDetailSwagger)
    @check_for_tenant
    def put(self, request, pk):
        users = User.objects.filter(tenant_id=request.user.tenant_id)
        group = get_object_or_404(Group, pk=pk, user__in=users)
        serializer = GroupSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(responses={})
    def delete(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        group.delete()
        return Response({}, 204)
