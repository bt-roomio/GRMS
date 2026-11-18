import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.base import AuthError
from django.conf import settings
from django.contrib.auth import get_user_model

from users.auth.errors import SocialLoginError, social_login_error_redirect

User = get_user_model()


logger = logging.getLogger(__name__)

FRONTEND_DOMAIN = settings.FRONTEND_DOMAIN


class NoSignupAccountAdapter(DefaultAccountAdapter):
    def respond_user_inactive(self, request, user):
        """
        Called when an inactive user tries to log in.
        Redirect to frontend instead of showing the default template.
        """
        return social_login_error_redirect(SocialLoginError.USER_INACTIVE)

    def is_open_for_signup(self, request):  # pyright: ignore
        return False

    def get_login_redirect_url(self, request):
        next_url = request.GET.get("next") or FRONTEND_DOMAIN
        logger.info("Login redirect for user=%s to next=%s", getattr(request, "user", None), next_url)
        return f"/api/v1/users/callback/?next={next_url}"


class NoNewSocialSignupAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):  # pyright: ignore
        email = (sociallogin.user and sociallogin.user.email) or None
        if not email:
            raise ImmediateHttpResponse(social_login_error_redirect(SocialLoginError.NO_EMAIL))

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            raise ImmediateHttpResponse(social_login_error_redirect(SocialLoginError.NO_USER))

        if sociallogin.is_existing:
            if sociallogin.user and sociallogin.user.is_active:
                return
            # Social account is connected to an inactive user — reconnect to active one
            sociallogin.user = user

        sociallogin.connect(request, user)

    def on_authentication_error(self, request, provider, error=None, exception=None, extra_context=None):
        extra_context = extra_context or {}
        logger.warning(
            "Social auth error: provider=%s error=%s exception=%r state_found=%s state_id=%s "
            "session_key=%s user=%s provider_error=%s provider_error_description=%s",
            getattr(provider, "id", provider),
            error,
            exception,
            extra_context.get("state") is not None,
            extra_context.get("state_id"),
            bool(request.session.session_key),
            getattr(request, "user", None),
            request.GET.get("error"),
            request.GET.get("error_description"),
            exc_info=exception if isinstance(exception, BaseException) else None,
        )
        code = (
            SocialLoginError.LOGIN_CANCELLED if error == AuthError.CANCELLED else SocialLoginError.AUTHENTICATION_ERROR
        )
        raise ImmediateHttpResponse(social_login_error_redirect(code))

    def pre_social_token(self, request, socialtoken):
        if not socialtoken or not socialtoken.token:
            raise ImmediateHttpResponse(social_login_error_redirect(SocialLoginError.TOKEN_ERROR))
