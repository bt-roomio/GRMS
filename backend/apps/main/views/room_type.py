from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from core.utils.permission import check_perms
from main.models import RoomType
from main.serializers.room_type import RoomTypeFilterParams, RoomTypeSerializer
from main.swagger.room_type import RoomTypeDetailSwagger, RoomTypeSwagger


class RoomTypeListView(APIView):
    @swagger_auto_schema(tags=["Main, RoomType"], responses=RoomTypeSwagger, query_serializer=RoomTypeFilterParams())
    @check_perms(["main.view_roomtype"])
    def get(self, request):
        params = RoomTypeFilterParams.check(request.GET)
        queryset = RoomType.objects.list(
            tenant=request.user.tenant,
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
        )
        serializer = RoomTypeSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))
        return Response(data)

    @swagger_auto_schema(tags=["Main, RoomType"], responses=RoomTypeSwagger, request_body=RoomTypeSerializer)
    @check_perms(["main.add_roomtype"])
    def post(self, request):
        data = request.data.copy()
        data["tenant"] = request.user.tenant_id
        serializer = RoomTypeSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, 201)


class RoomTypeDetailView(APIView):
    @swagger_auto_schema(tags=["Main, RoomType"], responses=RoomTypeDetailSwagger)
    @check_perms(["main.view_roomtype"])
    def get(self, request, pk):
        room_type = get_object_or_404(RoomType, pk=pk, tenant=request.user.tenant)
        serializer = RoomTypeSerializer(room_type)
        return Response(serializer.data)

    @swagger_auto_schema(tags=["Main, RoomType"], responses=RoomTypeDetailSwagger, request_body=RoomTypeSerializer)
    @check_perms(["main.change_roomtype"])
    def put(self, request, pk):
        data = request.data.copy()
        data["tenant"] = request.user.tenant_id
        instance = get_object_or_404(RoomType, pk=pk, tenant=request.user.tenant)
        serializer = RoomTypeSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(tags=["Main, RoomType"], responses={})
    @check_perms(["main.delete_roomtype"])
    def delete(self, request, pk):
        instance = get_object_or_404(RoomType, pk=pk, tenant=request.user.tenant)
        instance.delete()
        return Response({}, 204)
