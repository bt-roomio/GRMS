from access_manager.models import GroupStaff, Staff
from access_manager.serializers.staff import StaffFilterParams, StaffSerializer
from access_manager.swagger.staff import staff_swagger

from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from core.utils.perform_request import with_tenant


class StaffListView(APIView):
    @staff_swagger()
    def get(self, request):
        params = StaffFilterParams.check(request.GET)
        queryset = Staff.objects.list(  # pyright: ignore
            tenant_id=request.user.tenant_id,
            sort_by=params.get("sort_by", []),  # pyright: ignore
            search_field=params.get("search_field"),  # pyright: ignore
            search_value=params.get("search_value"),  # pyright: ignore
        )
        serializer = StaffSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)

    @staff_swagger()
    def post(self, request):
        data = with_tenant(request)
        serializer = StaffSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user, is_active=True)
        return Response(serializer.data, 201)


class StaffDetailView(APIView):
    @staff_swagger()
    def get(self, request, pk):
        instance = get_object_or_404(Staff, pk=pk, tenant_id=request.user.tenant_id, is_active=True)
        serializer = StaffSerializer(instance)
        return Response(serializer.data)

    @staff_swagger()
    def put(self, request, pk):
        data = with_tenant(request)
        instance = get_object_or_404(Staff, id=pk, tenant_id=request.user.tenant_id, is_active=True)
        serializer = StaffSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @staff_swagger()
    def delete(self, request, pk):
        instance = get_object_or_404(Staff, id=pk, tenant_id=request.user.tenant_id, is_active=True)
        instance.is_active = False
        instance.save()
        GroupStaff.objects.filter(staff=instance).delete()
        return Response({}, 204)
