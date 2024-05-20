from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from users.serializers.user import UserSerializer


class UserDetailView(APIView):
    @swagger_auto_schema(
        responses={
            200: UserSerializer(),
            401: "Authentication credentials were not provided.",
        }
    )
    def get(self, request):
        user = get_object_or_404(User, id=request.user.id)
        serializer = UserSerializer(user)
        return Response(serializer.data)
