from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom variant that first tries the Authorization header,
    and if there is none, takes access_token from HttpOnly cookies.
    """

    def authenticate(self, request):
        # 1. First the regular check via the Authorization header
        header_auth = super().authenticate(request)
        if header_auth:
            return header_auth

        # 2. Try to get the token from cookies
        access_token = request.COOKIES.get("access_token")
        if not access_token:
            return None  # no token at all

        validated_token = self.get_validated_token(access_token)
        user = self.get_user(validated_token)
        return (user, validated_token)
