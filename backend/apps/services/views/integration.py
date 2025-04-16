from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.views import APIView
from rest_framework.response import Response

from services.models import Integration
from services.serializers.integration import IntegrationSerializer
from services.swagger.integration import (
    integration_swagger_list,
    integration_swagger_retrive,
    integration_swagger_update,
)


class IntegrationListView(APIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["name"]
    search_fields = ["name", "type"]

    def get_queryset(self):
        return Integration.objects.filter(
            is_active=True,
            tenant=self.request.user.tenant,
        )

    @integration_swagger_list()
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Apply filters
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)

        serializer = IntegrationSerializer(queryset, many=True)
        return Response(serializer.data)


class IntegrationDetailView(APIView):
    def get_object(self, pk):
        try:
            return Integration.objects.get(pk=pk, is_active=True, tenant=self.request.user.tenant)
        except Integration.DoesNotExist:
            return None

    @integration_swagger_retrive()
    def get(self, request, pk, *args, **kwargs):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = IntegrationSerializer(instance)
        return Response(serializer.data)

    @integration_swagger_update()
    def put(self, request, pk, *args, **kwargs):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = IntegrationSerializer(instance, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, *args, **kwargs):
        return Response({"detail": 'Method "PATCH" not allowed.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
