from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Device, PublicSpace, Room
from services.serializers.lockkeys import (
    PublicSpaceLockKeySerializer,
    RoomLockKeySerializer,
)
from services.utils.permissions import DoorLockPermission
from shuttle.views.json_rpc import prepare_mqtt_request


class LockKeyDoorsListView(APIView):
    permission_classes = (DoorLockPermission,)

    def get(self, request):
        rooms = Room.objects.by_tenant(request.tenant).door_lock_devices()
        public_spaces = PublicSpace.objects.filter(tenant=request.tenant).prefetch_related(
            "device_public_spaces__device"
        )
        rooms_data = RoomLockKeySerializer(rooms, many=True).data
        public_spaces_data = PublicSpaceLockKeySerializer(public_spaces, many=True).data
        return Response([*rooms_data, *public_spaces_data])


class LockKeyDoorOpenView(APIView):
    permission_classes = (DoorLockPermission,)

    def post(self, request, space_id):
        device = get_object_or_404(Device, pk=space_id)
        result = prepare_mqtt_request(device, "unlock", {}, 33)
        return Response(result)


"""
    {
    "targetDeviceUUID": "5aab4f30-3e46-4ae5-9200-0ec6f51aa344",
            "topic": "v1/gateway/rpc",
            "data": {
                "device": "bc:e3:5c:0e:d3:e4",
                "data": {
                    "id": "345678",
                    "method": "unlock",
                    "params": {},
                    "timeout": 10000,
                },
            },
        }
"""
