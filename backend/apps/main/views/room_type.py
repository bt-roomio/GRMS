from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from core.utils.pagination import pagination
from main.models import RoomType
from main.serializers.room_type import RoomTypeSerializer, RoomTypeFilterParams


class RoomTypeListView(APIView):
    def get(self, request):
        params = RoomTypeFilterParams.check(request.GET)
        queryset = RoomType.objects.filter(tenant=request.user.tenant)
        serializer = RoomTypeSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))
        return Response(data)

    def post(self, request):
        serializer = RoomTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant=request.user.tenant)
        return Response(serializer.data)


class RoomTypeDetailView(APIView):
    def get(self, request, pk):
        room_type = get_object_or_404(RoomType, pk=pk, tenant=request.user.tenant)
        serializer = RoomTypeSerializer(room_type)
        return Response(serializer.data)

    def put(self, request, pk):
        instance = get_object_or_404(RoomType, pk=pk, tenant=request.user.tenant)
        serializer = RoomTypeSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        instance = get_object_or_404(RoomType, pk=pk, tenant=request.user.tenant)
        instance.delete()
        return Response({}, status=204)
