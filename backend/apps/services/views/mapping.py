from django.db import transaction

from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from services.mapping.constants import Direction
from services.mapping.engine import SKIP, MappingError, ranges_to_external, to_external, to_grms
from services.models import MappingOverride, MappingProfile
from services.serializers.mapping import (
    MappingOverrideFilterSerializer,
    MappingOverrideSerializer,
    MappingProfileFilterSerializer,
    MappingProfileSerializer,
    MappingProfileWriteSerializer,
    MappingTestSerializer,
)
from services.swagger.mapping import (
    mapping_override_swagger_create,
    mapping_override_swagger_delete,
    mapping_override_swagger_list,
    mapping_override_swagger_retrieve,
    mapping_override_swagger_update,
    mapping_profile_swagger_create,
    mapping_profile_swagger_delete,
    mapping_profile_swagger_list,
    mapping_profile_swagger_retrieve,
    mapping_profile_swagger_test,
    mapping_profile_swagger_update,
)


class MappingProfileListView(APIView):
    @mapping_profile_swagger_list()
    @check_perms(["services.view_mappingprofile"])
    def get(self, request):
        params = MappingProfileFilterSerializer.parse(request.query_params)
        queryset = MappingProfile.objects.list(request.user.tenant_id, params.search, params.integrator, params.sort_by)
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


class MappingProfileTestView(APIView):
    """Run one rule of a profile on a value: a dry run for checking a profile before using it."""

    @mapping_profile_swagger_test()
    @check_perms(["services.view_mappingprofile"])
    def post(self, request, pk):
        profile = get_object_or_404(MappingProfile.objects.by_tenant(request.user.tenant_id), pk=pk)
        serializer = MappingTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        rule = profile.rules.select_related("tag_type").filter(code=data["rule"]).first()
        if rule is None:
            return Response({"rule": ["No such rule in the profile."]}, status=status.HTTP_400_BAD_REQUEST)
        rule = rule.as_rule()
        try:
            if data["direction"] == Direction.TO_EXTERNAL:
                result = {"output": to_external(rule, data["input"])}
                if data["tag_ranges"] is not None:
                    result["tag_ranges"] = ranges_to_external(rule, data["tag_ranges"])
            else:
                output = to_grms(rule, data["input"], data["tag_ranges"])
                result = {"output": None, "skipped": True} if output is SKIP else {"output": output}
        except MappingError as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class MappingOverrideListView(APIView):
    @mapping_override_swagger_list()
    @check_perms(["services.view_mappingoverride"])
    def get(self, request):
        params = MappingOverrideFilterSerializer.parse(request.query_params)
        queryset = MappingOverride.objects.list(request.user.tenant_id, params.integration, params.level)
        serializer = MappingOverrideSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.page, params.size)
        return Response(data)

    @mapping_override_swagger_create()
    @check_perms(["services.add_mappingoverride"])
    def post(self, request):
        serializer = MappingOverrideSerializer(data=request.data, context={"tenant_id": request.user.tenant_id})
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MappingOverrideDetailView(APIView):
    """A tenant reads, changes and deletes only the overrides of its own integrations."""

    def get_own_object(self, request, pk):
        return get_object_or_404(MappingOverride.objects.by_tenant(request.user.tenant_id), pk=pk)

    @mapping_override_swagger_retrieve()
    @check_perms(["services.view_mappingoverride"])
    def get(self, request, pk):
        return Response(MappingOverrideSerializer(self.get_own_object(request, pk)).data)

    @mapping_override_swagger_update()
    @check_perms(["services.change_mappingoverride"])
    def put(self, request, pk):
        instance = self.get_own_object(request, pk)
        serializer = MappingOverrideSerializer(instance, request.data, context={"tenant_id": request.user.tenant_id})
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    @mapping_override_swagger_delete()
    @check_perms(["services.delete_mappingoverride"])
    def delete(self, request, pk):
        self.get_own_object(request, pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
