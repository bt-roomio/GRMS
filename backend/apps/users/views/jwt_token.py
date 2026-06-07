from drf_yasg.utils import swagger_auto_schema
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.serializers.jwt_token import CustomTokenObtainPairSerializer


class AuthTokenThrottle(AnonRateThrottle):
    scope = "auth_token"

    def get_ident(self, request):
        # CF-Connecting-IP → X-Real-IP (nginx-set) → REMOTE_ADDR.
        # X-Forwarded-For намеренно не используется: leftmost-запись
        # контролируется клиентом и позволяет обойти throttle.
        return (
            request.META.get("HTTP_CF_CONNECTING_IP")
            or request.META.get("HTTP_X_REAL_IP")
            or request.META.get("REMOTE_ADDR", "unknown")
        )


class CustomTokenRefreshView(TokenRefreshView):
    throttle_classes = [AuthTokenThrottle]

    @swagger_auto_schema(tags=["Users, JWT"])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [AuthTokenThrottle]

    @swagger_auto_schema(tags=["Users, JWT"])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
