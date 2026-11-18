from enum import StrEnum
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect


class SocialLoginError(StrEnum):
    """Codes sent to the frontend login page as `?error=` when a social login fails."""

    NO_EMAIL = "no_email"
    NO_USER = "no_user"
    USER_INACTIVE = "user_inactive"
    NO_SOCIAL_ACCOUNT = "no_social_account"
    LOGIN_CANCELLED = "login_cancelled"
    AUTHENTICATION_ERROR = "authentication_error"
    TOKEN_ERROR = "token_error"


SOCIAL_LOGIN_ERROR_MESSAGES = {
    SocialLoginError.NO_EMAIL: "The sign-in provider did not share an email address for this account.",
    SocialLoginError.NO_USER: "No active user is registered with this email. Please contact your administrator.",
    SocialLoginError.USER_INACTIVE: "This account is inactive. Please contact your administrator.",
    SocialLoginError.NO_SOCIAL_ACCOUNT: "This account is not linked to a sign-in provider. Please try again.",
    SocialLoginError.LOGIN_CANCELLED: "Sign-in was cancelled.",
    SocialLoginError.AUTHENTICATION_ERROR: (
        "Sign-in with the provider failed. Please try again or contact your administrator."
    ),
    SocialLoginError.TOKEN_ERROR: "The sign-in provider did not return an access token. Please try again.",
}


def social_login_error_redirect(code: SocialLoginError):
    """Redirect to the frontend login page carrying the error code and a readable message."""
    query = urlencode({"error": code.value, "message": SOCIAL_LOGIN_ERROR_MESSAGES[code]})
    return redirect(f"{settings.FRONTEND_DOMAIN}/auth/login/?{query}")
