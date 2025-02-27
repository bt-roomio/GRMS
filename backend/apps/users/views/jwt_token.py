from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class CustomTokenRefreshView(TokenRefreshView):

    @swagger_auto_schema(tags=["Users, JWT"])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Normalize the email/email to lowercase.
        email = attrs.get("email")
        if email:
            attrs["email"] = email.lower()
        return super().validate(attrs)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @swagger_auto_schema(tags=["Users, JWT"])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
