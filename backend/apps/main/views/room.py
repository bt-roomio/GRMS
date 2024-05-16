from django.apps.registry import partial
from django.utils.translation.trans_null import activate
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import Http404, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from main.swagger.room import RoomSwagger
from core.utils.pagination import pagination
from core.utils.permission import check_for_tenant
from main.models import Room
from main.serializers.room import RoomFilterParams, RoomSerializer


class RoomListView(APIView):
    @swagger_auto_schema(responses=RoomSwagger)
    @check_for_tenant
    def get(self, request):
        params = RoomFilterParams.check(request.GET)
        queryset = Room.objects.by_tenant(tenant=request.user.tenant)
        if not queryset:
            raise Http404('Rooms for this tenant not found!')
        serializer = RoomSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get('page'), params.get('size'))
        return Response(data)

    @check_for_tenant
    def post(self, request):
        serializer = RoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data, 201)


class RoomDetailView(APIView):
    @check_for_tenant
    def get(self, request, pk):
        queryset = get_object_or_404(Room, id=pk, active=True)
        serializer = RoomSerializer(queryset)
        return Response(serializer.data)

    @check_for_tenant
    def put(self, request, pk):
        instance = get_object_or_404(Room, id=pk, active=True)
        serializer = RoomSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    @check_for_tenant
    def delete(self, request, pk):
        instance = get_object_or_404(Room, id=pk, active=True)
        instance.active = False
        instance.save(updated_by=request.user)
        return Response({}, 204)
