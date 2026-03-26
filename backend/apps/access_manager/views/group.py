from access_manager.models import Group, GroupRoom
from access_manager.serializers.group import GroupFilterParams, GroupSerializer
from access_manager.swagger.group import group_swagger
from django.db.models import Count, Q

from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from core.utils.perform_request import with_tenant
from core.utils.permission import check_perms


class GroupListView(APIView):
    @group_swagger("list")
    @check_perms(["access_manager.view_group"])
    def get(self, request):
        params = GroupFilterParams.check(request.GET)
        queryset = Group.objects.list(
            tenant_id=request.user.tenant_id,
            sort_by=params.get("sort_by", []),
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
        )
        serializer = GroupSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)

    @group_swagger()
    @check_perms(["access_manager.add_group"])
    def post(self, request):
        data = with_tenant(request)
        serializer = GroupSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, 201)


class GroupDetailView(APIView):
    @group_swagger()
    @check_perms(["access_manager.view_group"])
    def get(self, request, pk):
        instance = get_object_or_404(
            Group.objects.filter(
                pk=pk,
                tenant_id=request.user.tenant_id,
                is_active=True,
            ).annotate(count_staff=Count("staff", filter=Q(staff__is_active=True))),
        )
        serializer = GroupSerializer(instance)
        return Response(serializer.data)

    @group_swagger()
    @check_perms(["access_manager.change_group"])
    def put(self, request, pk):
        data = with_tenant(request)
        instance = get_object_or_404(Group, id=pk, tenant_id=request.user.tenant_id, is_active=True)
        serializer = GroupSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    @group_swagger()
    @check_perms(["access_manager.delete_group"])
    def delete(self, request, pk):
        instance = get_object_or_404(Group, id=pk, tenant_id=request.user.tenant_id, is_active=True)
        instance.is_active = False
        instance.updated_by = request.user
        instance.save()
        GroupRoom.objects.filter(group=instance).delete()
        return Response({}, 204)
