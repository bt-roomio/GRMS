from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Кастомный вариант, который сначала пробует Authorization header,
    а если нет — достаёт access_token из HttpOnly cookies.
    """

    def authenticate(self, request):
        # 1. Сначала обычная проверка через Authorization header
        header_auth = super().authenticate(request)
        if header_auth:
            return header_auth

        # 2. Попробуем достать токен из cookies
        access_token = request.COOKIES.get("access_token")
        if not access_token:
            return None  # токена нет вообще

        validated_token = self.get_validated_token(access_token)
        user = self.get_user(validated_token)
        return (user, validated_token)
