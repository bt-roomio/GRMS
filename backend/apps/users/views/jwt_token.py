from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.serializers.jwt_token import CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    @swagger_auto_schema(tags=["Users, JWT"])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @swagger_auto_schema(tags=["Users, JWT"])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
