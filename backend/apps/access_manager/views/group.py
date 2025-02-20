from access_manager.models import Group, GroupRoom
from access_manager.serializers.group import GroupFilterParams, GroupSerializer
from access_manager.swagger.group import group_swagger

from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from core.utils.perform_request import with_tenant


class GroupListView(APIView):
    @group_swagger("list")
    def get(self, request):
        params = GroupFilterParams.check(request.GET)
        queryset = Group.objects.list(  # pyright: ignore
            tenant_id=request.user.tenant_id,
            sort_by=params.get("sort_by", []),  # pyright: ignore
            search_field=params.get("search_field"),  # pyright: ignore
            search_value=params.get("search_value"),  # pyright: ignore
        )
        serializer = GroupSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)

    @group_swagger()
    def post(self, request):
        data = with_tenant(request)
        serializer = GroupSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, 201)


class GroupDetailView(APIView):
    @group_swagger()
    def get(self, request, pk):
        instance = get_object_or_404(Group, pk=pk, tenant_id=request.user.tenant_id, is_active=True)
        serializer = GroupSerializer(instance)
        return Response(serializer.data)

    @group_swagger()
    def put(self, request, pk):
        data = with_tenant(request)
        instance = get_object_or_404(Group, id=pk, tenant_id=request.user.tenant_id, is_active=True)
        serializer = GroupSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    @group_swagger()
    def delete(self, request, pk):
        instance = get_object_or_404(Group, id=pk, tenant_id=request.user.tenant_id, is_active=True)
        instance.is_active = False
        instance.save(updated_by=request.user)
        GroupRoom.objects.filter(group=instance).delete()
        return Response({}, 204)
