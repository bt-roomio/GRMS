from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response

from services.models import Integration
from services.serializers.integration import IntegrationSerializer
from services.swagger.integration import (
    integration_swagger_list,
    integration_swagger_retrive,
    integration_swagger_update,
)


class InegrationListView(ListAPIView):
    model = Integration
    queryset = Integration.objects.filter(is_active=True, enable=True)
    serializer_class = IntegrationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["name"]
    search_fields = ["name", "type"]

    @integration_swagger_list()
    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(tenant=request.user.tenant)
        return super().get(request, *args, **kwargs)


class InegrationDetailView(RetrieveUpdateAPIView):
    model = Integration
    queryset = Integration.objects.filter(is_active=True, enable=True)
    serializer_class = IntegrationSerializer
    http_method_names = ["get", "put"]

    @integration_swagger_retrive()
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @integration_swagger_update()
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def patch(self):
        return Response({"detail": 'Method "PATCH" not allowed.'}, 405)
