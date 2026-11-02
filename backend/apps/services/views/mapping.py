from django.db import transaction

from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from services.models import MappingProfile
from services.serializers.mapping import (
    MappingProfileFilterSerializer,
    MappingProfileSerializer,
    MappingProfileWriteSerializer,
)
from services.swagger.mapping import (
    mapping_profile_swagger_create,
    mapping_profile_swagger_delete,
    mapping_profile_swagger_list,
    mapping_profile_swagger_retrieve,
    mapping_profile_swagger_update,
)


class MappingProfileListView(APIView):
    @mapping_profile_swagger_list()
    @check_perms(["services.view_mappingprofile"])
    def get(self, request):
        params = MappingProfileFilterSerializer.parse(request.query_params)
        queryset = MappingProfile.objects.list(
            request.user.tenant_id, params.search, params.integrator, params.scope, params.sort_by
        )
        serializer = MappingProfileSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.page, params.size)
        return Response(data)

    @mapping_profile_swagger_create()
    @check_perms(["services.add_mappingprofile"])
    def post(self, request):
        tenant_id = request.user.tenant_id
        serializer = MappingProfileWriteSerializer(data=request.data, context={"tenant_id": tenant_id})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            instance = serializer.save(tenant_id=tenant_id, created_by=request.user)
        return Response(MappingProfileSerializer(instance).data, status=status.HTTP_201_CREATED)


class MappingProfileDetailView(APIView):
    """A tenant reads, changes and deletes only its own mapping profiles."""

    def get_own_object(self, request, pk):
        return get_object_or_404(MappingProfile.objects.by_tenant(request.user.tenant_id).with_rules(), pk=pk)

    @mapping_profile_swagger_retrieve()
    @check_perms(["services.view_mappingprofile"])
    def get(self, request, pk):
        return Response(MappingProfileSerializer(self.get_own_object(request, pk)).data)

    @mapping_profile_swagger_update()
    @check_perms(["services.change_mappingprofile"])
    def put(self, request, pk):
        instance = self.get_own_object(request, pk)
        serializer = MappingProfileWriteSerializer(
            instance, request.data, context={"tenant_id": request.user.tenant_id}
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            instance = serializer.save(updated_by=request.user)
        return Response(MappingProfileSerializer(self.get_own_object(request, instance.pk)).data)

    @mapping_profile_swagger_delete()
    @check_perms(["services.delete_mappingprofile"])
    def delete(self, request, pk):
        self.get_own_object(request, pk).delete()  # integrations using it fall back to GRMS values
        return Response(status=status.HTTP_204_NO_CONTENT)
