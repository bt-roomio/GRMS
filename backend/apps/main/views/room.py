from django.apps.registry import partial
from django.utils.translation.trans_null import activate
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import Http404, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_for_tenant
from main.swagger.room import RoomDetailSwagger, RoomSwagger
from core.utils.pagination import pagination
from main.models import Room
from main.serializers.room import RoomFilterParams, RoomSerializer


class RoomListView(APIView):
    @swagger_auto_schema(responses=RoomSwagger, query_serializer=RoomFilterParams)
    @check_for_tenant
    def get(self, request):
        params = RoomFilterParams.check(request.GET)
        queryset = Room.objects.list(
            tenant=request.user.tenant,
            status=params.get("status"),
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
            sort_by=params.get("sort_by"),
        )
        if not queryset:
            raise Http404("Rooms for this tenant not found!")
        serializer = RoomSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size", 15))
        return Response(data)

    @swagger_auto_schema(responses=RoomSwagger, request_body=RoomSerializer)
    @check_for_tenant
    def post(self, request):
        serializer = RoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data, 201)


class RoomDetailView(APIView):
    @swagger_auto_schema(responses=RoomDetailSwagger)
    @check_for_tenant
    def get(self, request, pk):
        queryset = get_object_or_404(Room, id=pk, active=True)
        serializer = RoomSerializer(queryset)
        return Response(serializer.data)

    @swagger_auto_schema(responses=RoomDetailSwagger, request_body=RoomSerializer)
    @check_for_tenant
    def put(self, request, pk):
        instance = get_object_or_404(Room, id=pk, active=True)
        serializer = RoomSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    @swagger_auto_schema(responses={})
    @check_for_tenant
    def delete(self, request, pk):
        instance = get_object_or_404(Room, id=pk, active=True)
        instance.active = False
        instance.updated_by = request.user
        instance.save()
        return Response({}, 204)
