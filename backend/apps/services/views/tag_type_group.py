from django.db.models import ProtectedError

from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from services.models import TagTypeGroup
from services.serializers.tag_type_group import (
    TagTypeGroupFilterSerializer,
    TagTypeGroupSerializer,
    TagTypeGroupWriteSerializer,
)
from services.swagger.tag_type_group import (
    tag_type_group_swagger_create,
    tag_type_group_swagger_delete,
    tag_type_group_swagger_list,
    tag_type_group_swagger_retrieve,
    tag_type_group_swagger_update,
)


class TagTypeGroupListView(APIView):
    @tag_type_group_swagger_list()
    @check_perms(["services.view_tagtypegroup"])
    def get(self, request):
        params = TagTypeGroupFilterSerializer.parse(request.query_params)
        queryset = TagTypeGroup.objects.list(request.user.tenant_id, params.search, params.sort_by)
        serializer = TagTypeGroupSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.page, params.size)
        return Response(data)

    @tag_type_group_swagger_create()
    @check_perms(["services.add_tagtypegroup"])
    def post(self, request):
        tenant_id = request.user.tenant_id
        serializer = TagTypeGroupWriteSerializer(data=request.data, context={"tenant_id": tenant_id})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(tenant_id=tenant_id, created_by=request.user)
        return Response(TagTypeGroupSerializer(instance).data, status=status.HTTP_201_CREATED)


class TagTypeGroupDetailView(APIView):
    """A tenant reads, changes and deletes only its own tag type groups."""

    def get_own_object(self, request, pk):
        return get_object_or_404(TagTypeGroup.objects.by_tenant(request.user.tenant_id), pk=pk)

    @tag_type_group_swagger_retrieve()
    @check_perms(["services.view_tagtypegroup"])
    def get(self, request, pk):
        return Response(TagTypeGroupSerializer(self.get_own_object(request, pk)).data)

    @tag_type_group_swagger_update()
    @check_perms(["services.change_tagtypegroup"])
    def put(self, request, pk):
        instance = self.get_own_object(request, pk)
        tenant_id = request.user.tenant_id
        serializer = TagTypeGroupWriteSerializer(instance, request.data, context={"tenant_id": tenant_id})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(updated_by=request.user)
        return Response(TagTypeGroupSerializer(instance).data)

    @tag_type_group_swagger_delete()
    @check_perms(["services.delete_tagtypegroup"])
    def delete(self, request, pk):
        try:
            self.get_own_object(request, pk).delete()
        except ProtectedError:  # TagType.group is PROTECT
            return Response(
                {"detail": "The tag type group still has tag types and cannot be deleted."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
