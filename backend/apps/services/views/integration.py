from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from services.models import Integration
from services.serializers.integration import IntegrationParams, IntegrationSerializer
from services.swagger.integration import (
    integration_swagger_list,
    integration_swagger_retrive,
    integration_swagger_update,
)


class IntegrationListView(APIView):
    @integration_swagger_list()
    def get(self, request):
        params = IntegrationParams.check(request.GET)
        page, size = params.pop("page"), params.pop("size")
        queryset = Integration.objects.list(tenant_id=request.user.tenant_id, **params)
        serializer = IntegrationSerializer(queryset, many=True)
        data = pagination(queryset, serializer, page, size)
        return Response(data)


class IntegrationDetailView(APIView):
    @integration_swagger_retrive()
    @check_perms(["services.view_integration"])
    def get(self, request, pk):
        instance = get_object_or_404(Integration, pk=pk, is_active=True, enable=True, tenant_id=request.user.tenant_id)
        serializer = IntegrationSerializer(instance)
        return Response(serializer.data)

    @integration_swagger_update()
    @check_perms(["services.change_integration"])
    def put(self, request, pk):
        instance = get_object_or_404(Integration, pk=pk, is_active=True, enable=True, tenant_id=request.user.tenant_id)
        serializer = IntegrationSerializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)
