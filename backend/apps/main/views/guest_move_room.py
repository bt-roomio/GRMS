from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Guest
from main.serializers.guest import GuestMoveRoomSerializer, GuestMoveRoomFilterParams


class GuestMoveRoomListView(APIView):
    def put(self, request):
        params = GuestMoveRoomFilterParams.check(request.GET)
        instance = Guest.objects.filter(room_id=params.get("from_room"))
        if not instance.exists():
            return Response({"detail": "`from_room` guests doesn't exist!"}, 404)
        serializer = GuestMoveRoomSerializer(instance, data={"to_room": params.get("to_room").id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Guests moved successfully!"}, 200)
