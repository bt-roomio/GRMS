from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Device, PublicSpace, Room
from services.serializers.lockkeys import (
    PublicSpaceLockKeySerializer,
    RoomLockKeySerializer,
)
from services.swagger.lockkeys import lockkeys_door_open_swagger, lockkeys_doors_list_swagger
from services.utils.permissions import DoorLockPermission
from shuttle.views.json_rpc import prepare_mqtt_request


class LockKeyDoorsListView(APIView):
    permission_classes = (DoorLockPermission,)

    @lockkeys_doors_list_swagger()
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

    @lockkeys_door_open_swagger()
    def post(self, request, space_id):
        device = get_object_or_404(Device, pk=space_id)
        result = prepare_mqtt_request(device, "unlock", {}, 33)
        return Response(result)
