from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from hoteza.serializers.guest_change import GuestChangeSerializer


class GuestChangeListView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = GuestChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"result": 0, "message": "Successfully guestchanged!"})
