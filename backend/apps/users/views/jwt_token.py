from drf_yasg.utils import swagger_auto_schema
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.utils.ip import get_client_ip
from users.serializers.jwt_token import CustomTokenObtainPairSerializer


class AuthTokenThrottle(AnonRateThrottle):
    scope = "auth_token"

    def get_ident(self, request):
        return get_client_ip(request)


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
