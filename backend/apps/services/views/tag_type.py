from django.db import transaction

from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from services.models import TagType
from services.serializers.tag_type import TagTypeFilterSerializer, TagTypeSerializer, TagTypeWriteSerializer
from services.swagger.tag_type import (
    tag_type_swagger_create,
    tag_type_swagger_delete,
    tag_type_swagger_list,
    tag_type_swagger_retrieve,
    tag_type_swagger_update,
)


class TagTypeListView(APIView):
    @tag_type_swagger_list()
    @check_perms(["services.view_tagtype"])
    def get(self, request):
        params = TagTypeFilterSerializer.parse(request.query_params)
        queryset = TagType.objects.list(request.user.tenant_id, params.search, params.group, params.sort_by)
        serializer = TagTypeSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.page, params.size)
        return Response(data)

    @tag_type_swagger_create()
    @check_perms(["services.add_tagtype"])
    def post(self, request):
        tenant_id = request.user.tenant_id
        serializer = TagTypeWriteSerializer(data=request.data, context={"tenant_id": tenant_id})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            instance = serializer.save(tenant_id=tenant_id, created_by=request.user)
        return Response(TagTypeSerializer(instance).data, status=status.HTTP_201_CREATED)


class TagTypeDetailView(APIView):
    """A tenant reads, changes and deletes only its own tag types."""

    def get_own_object(self, request, pk):
        return get_object_or_404(TagType.objects.by_tenant(request.user.tenant_id), pk=pk)

    def save(self, request, pk, partial):
        instance = self.get_own_object(request, pk)
        tenant_id = request.user.tenant_id
        serializer = TagTypeWriteSerializer(instance, request.data, partial=partial, context={"tenant_id": tenant_id})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            instance = serializer.save(updated_by=request.user)
        return Response(TagTypeSerializer(instance).data)

    @tag_type_swagger_retrieve()
    @check_perms(["services.view_tagtype"])
    def get(self, request, pk):
        return Response(TagTypeSerializer(self.get_own_object(request, pk)).data)

    @tag_type_swagger_update()
    @check_perms(["services.change_tagtype"])
    def put(self, request, pk):
        return self.save(request, pk, partial=False)

    @tag_type_swagger_delete()
    @check_perms(["services.delete_tagtype"])
    def delete(self, request, pk):
        self.get_own_object(request, pk).delete()
        return Response(status=204)
