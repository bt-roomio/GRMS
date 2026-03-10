from admin_panel.swagger.impersonate import ImpersonateSwagger

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.utils.permission import IsSuperUser
from users.models import User


class ImpersonateView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=ImpersonateSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Generates JWT tokens on behalf of the specified user.",
    )
    def post(self, _, user_id):
        user = get_object_or_404(User, id=user_id, is_active=True)
        refresh: RefreshToken = RefreshToken.for_user(user)  # pyright: ignore[reportAssignmentType]
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )
