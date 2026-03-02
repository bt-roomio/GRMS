from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.utils.permission import IsSuperUser
from users.models import User


class ImpersonateView(APIView):
    permission_classes = (IsSuperUser,)

    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id, is_active=True)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )
