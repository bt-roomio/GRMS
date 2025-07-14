from access_manager.models import GroupPublicSpace, GroupRoom, Staff, StaffCard
from access_manager.serializers.staff import StaffFilterParams, StaffSerializer
from access_manager.swagger.staff import staff_swagger
from access_manager.tasks.send_rpc import send_rpc_request

from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from core.utils.perform_request import with_tenant
from core.utils.permission import check_perms
from main.models import Device


class StaffListView(APIView):
    @staff_swagger()
    @check_perms(["access_manager.view_staff"])
    def get(self, request):
        params = StaffFilterParams.check(request.GET)
        queryset = Staff.objects.list(  # pyright: ignore
            tenant_id=request.user.tenant_id,
            sort_by=params.get("sort_by", []),  # pyright: ignore
            search_field=params.get("search_field"),  # pyright: ignore
            search_value=params.get("search_value"),  # pyright: ignore
            in_group=params.get("in_group"),  # pyright: ignore
            not_in_group=params.get("not_in_group"),  # pyright: ignore
        )
        serializer = StaffSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)

    @staff_swagger()
    @check_perms(["access_manager.add_staff"])
    def post(self, request):
        data = with_tenant(request)
        serializer = StaffSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user, is_active=True)
        return Response(serializer.data, 201)


class StaffDetailView(APIView):
    @staff_swagger()
    @check_perms(["access_manager.view_staff"])
    def get(self, request, pk):
        instance = get_object_or_404(Staff, pk=pk, tenant_id=request.user.tenant_id, is_active=True)
        serializer = StaffSerializer(instance)
        return Response(serializer.data)

    @staff_swagger()
    @check_perms(["access_manager.change_staff"])
    def put(self, request, pk):
        data = with_tenant(request)
        instance = get_object_or_404(Staff, id=pk, tenant_id=request.user.tenant_id, is_active=True)
        serializer = StaffSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @staff_swagger()
    @check_perms(["access_manager.delete_staff"])
    def delete(self, request, pk):
        instance = get_object_or_404(Staff, id=pk, tenant_id=request.user.tenant_id, is_active=True)
        user = str(request.user.id)

        group_rooms_devices = GroupRoom.objects.filter(group=instance.group, room__devices__is_active=True).values_list(
            "room__devices", flat=True
        )
        group_pub_spaces_devices = GroupPublicSpace.objects.filter(
            group=instance.group, public_space__device__is_active=True
        ).values_list("public_space__device", flat=True)

        devices = Device.objects.filter(id__in=[*group_rooms_devices, *group_pub_spaces_devices])
        cards = StaffCard.objects.filter(staff=instance).values_list("card__number", flat=True)

        results = []
        for device in devices:
            result = send_rpc_request(str(device.id), cards, False, staff_id=str(pk), user=user)
            results.append(result)

        instance.is_active = False
        instance.save()
        return Response({}, 204)
