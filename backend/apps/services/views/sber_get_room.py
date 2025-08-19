from rest_framework.permissions import AllowAny
from rest_framework.views import APIView, Response


class SberGetRoomDetailView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        body = request.data
        body["messageName"] = "ANSWER_TO_USER"
        body["payload"] = {
            "pronounceText": "Добро пожаловать, Amigo, в номер 412!",
            "auto_listening": False,
            "finished": True,
        }
        return Response(body)
