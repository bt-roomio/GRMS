from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from hoteza.serializers.checkout import CheckOutSerializer


class CheckOutListView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = CheckOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"result": 0, "message": "Successfully checkout!"})
