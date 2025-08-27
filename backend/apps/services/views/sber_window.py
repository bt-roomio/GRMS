from rest_framework.permissions import AllowAny
from rest_framework.views import APIView, Response

from main.models import Guest, Room


class SberWindowView(APIView):
    permission_classes = (AllowAny,)

    rus_list = (
        "UA",
        "MD",
        "GE",
        "AM",
        "AZ",
        "TJ",
        "UZ",
        "TM",
        "LV",
        "LT",
        "EE",
        "RU",
        "BY",
        "KZ",
        "KG",
    )

    def post(self, request):
        body = request.data
        sber_device_id = body.get("payload").get("device").get("deviceId")
        room = Room.objects.filter(additional_info__sber_device_id=sber_device_id).first()
        if not room:
            body["messageName"] = "ANSWER_TO_USER"
            body["payload"] = {
                "pronounceText": "Сбер девайс не найдено",
                "auto_listening": False,
                "finished": True,
            }
            return Response(body)
        guest = Guest.objects.list(tenant_id=room.tenant_id, room=room).first()
        if not guest:
            body["messageName"] = "ANSWER_TO_USER"
            body["payload"] = {
                "pronounceText": "Гостя не найдено",
                "auto_listening": False,
                "finished": True,
            }
            return Response(body)

        text = "Кондиционер не может быть включен, окно открыто"
        if guest.nationality and guest.nationality not in self.rus_list:
            from deep_translator import GoogleTranslator

            text = GoogleTranslator("ru", "en").translate(text)

        body["messageName"] = "ANSWER_TO_USER"
        body["payload"] = {
            "pronounceText": text,
            "auto_listening": False,
            "finished": True,
        }
        guest.additional_info = {"greeted": True}
        guest.save()
        return Response(body)
