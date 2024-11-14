from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from hoteza.serializers.dnd import DNDSerializer


class DNDListView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = DNDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"result": 0, "message": "Status of the room has been successfully changed to dnd!"})
