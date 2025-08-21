from rest_framework.permissions import AllowAny
from rest_framework.views import APIView, Response

from main.models import Guest, Room


class SberGetRoomDetailView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        body = request.data
        sber_device_id = body.get("payload").get("device").get("deviceId")
        room = Room.objects.filter(additional_info__sber_device_id=sber_device_id).first()
        if not room:
            body["messageName"] = "ANSWER_TO_USER"
            body["payload"] = {
                "pronounceText": "Ошибка, но мы уже работает над проблемой",  # TODO: answer
                "auto_listening": False,
                "finished": True,
            }
            return Response(body)
        guest = Guest.objects.list(tenant_id=room.tenant_id, room=room).first()
        if not guest:
            body["messageName"] = "ANSWER_TO_USER"
            body["payload"] = {
                "pronounceText": "Ошибка, но мы уже работает над проблемой",  # TODO: answer
                "auto_listening": False,
                "finished": True,
            }
            return Response(body)

        body["messageName"] = "ANSWER_TO_USER"
        body["payload"] = {
            "pronounceText": f"Добро пожаловать, {guest.lastname} {guest.name}, в номер {room.number}!",
            "auto_listening": False,
            "finished": True,
        }
        return Response(body)
