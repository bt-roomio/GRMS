from django.contrib.auth.models import Group
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.permission import IsTenantAndSysAdmin
from users.serializers.group import GroupSerializer
from users.swagger.groups import GroupsSwagger, GroupDetailSwagger


class GroupsListView(APIView):
    permission_classes = (IsTenantAndSysAdmin,)

    @swagger_auto_schema(operation_description="Getting all user groups.", responses=GroupsSwagger)
    def get(self, request):
        query = Group.objects.prefetch_related("permissions")
        query = query.filter(user=request.user) if not request.user.groups.filter(name="SYS_ADMIN") else query
        query = query.order_by("id")

        serializer = GroupSerializer(query, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Creating a group for exactly tenant.",
        responses=GroupDetailSwagger,
        request_body=GroupSerializer,
    )
    def post(self, request):
        instance = Group.objects.filter(name=request.data.get("name")).first()
        if instance and instance.name == "SYS_ADMIN" and not request.user.groups.filter(name="SYS_ADMIN"):
            raise ValidationError({"detail": "You don't have permission to create SYS_ADMIN."})
        serializer = GroupSerializer(instance, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, 201)


class GroupDetailView(APIView):
    permission_classes = [IsTenantAndSysAdmin]

    @swagger_auto_schema(responses=GroupDetailSwagger)
    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk, user=request.user)
        serializer = GroupSerializer(group)
        return Response(serializer.data)

    @swagger_auto_schema(responses=GroupDetailSwagger)
    def put(self, request, pk):
        group = get_object_or_404(Group, pk=pk, user=request.user)
        serializer = GroupSerializer(group, data=request.data, context={"request": request}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(responses={})
    def delete(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        group.delete()
        return Response({}, 204)
