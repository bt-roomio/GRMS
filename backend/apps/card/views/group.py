from card.models import Group
from card.serializers.group import GroupFilterParams, GroupSerializer
from card.swagger.group import group_swagger

from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from core.utils.perform_request import with_tenant


class GroupListView(APIView):
    @group_swagger()
    def get(self, request):
        params = GroupFilterParams.check(request.GET)
        queryset = Group.objects.list(
            tenant_id=request.user.tenant_id,
            sort_by=params.get("sort_by", []),
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
        )
        serializer = GroupSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))
        return Response(data)

    def post(self, request):
        data = with_tenant(request)
        serializer = GroupSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, 201)


class GroupDetailView(APIView):
    def get(self, request, pk):
        instance = get_object_or_404(Group, pk=pk, tenant_id=request.user.tenant_id, is_active=True)
        serializer = GroupSerializer(instance)
        return Response(serializer.data)

    def put(self, request, pk):
        data = with_tenant(request)
        instance = get_object_or_404(Group, id=pk, tenant_id=request.user.tenant_id, is_active=True)
        serializer = GroupSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        instance = get_object_or_404(Group, id=pk, tenant_id=request.user.tenant_id, is_active=True)
        instance.is_active = False
        instance.save()
        return Response({}, 204)
