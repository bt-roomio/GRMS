from core.utils.pagination import pagination
from core.utils.permission import check_perms
from drf_yasg.utils import swagger_auto_schema
from main.models import Room
from main.serializers.room import RoomFilterParams, RoomSerializer
from main.swagger.room import RoomDetailSwagger, RoomSwagger
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView


class RoomListView(APIView):
    @swagger_auto_schema(responses=RoomSwagger, query_serializer=RoomFilterParams())
    @check_perms(["main.view_room"])
    def get(self, request):
        params = RoomFilterParams.check(request.GET)
        queryset = Room.objects.list(
            tenant=request.user.tenant,
            state=params.get("state"),
            status=params.get("status"),
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
            sort_by=params.get("sort_by"),
        )
        serializer = RoomSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size", 15))
        return Response(data)

    @swagger_auto_schema(responses=RoomSwagger, request_body=RoomSerializer)
    @check_perms(["main.add_room"])
    def post(self, request):
        tenant_id = request.user.tenant_id
        data = request.data.copy()
        data["tenant"] = tenant_id
        serializer = RoomSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, 201)


class RoomDetailView(APIView):
    @swagger_auto_schema(responses=RoomDetailSwagger)
    @check_perms(["main.view_room"])
    def get(self, request, pk):
        queryset = get_object_or_404(Room, id=pk, active=True)
        serializer = RoomSerializer(queryset, context={"detail": True})
        return Response(serializer.data)

    @swagger_auto_schema(responses=RoomDetailSwagger, request_body=RoomSerializer)
    @check_perms(["main.change_room"])
    def put(self, request, pk):
        instance = get_object_or_404(Room, id=pk, active=True)
        serializer = RoomSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    @swagger_auto_schema(responses={})
    @check_perms(["main.delete_room"])
    def delete(self, request, pk):
        instance = get_object_or_404(Room, id=pk)
        instance.delete()
        return Response({}, 204)
