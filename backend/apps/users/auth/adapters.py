import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

User = get_user_model()


logger = logging.getLogger(__name__)

FRONTEND_DOMAIN = settings.FRONTEND_DOMAIN


class NoSignupAccountAdapter(DefaultAccountAdapter):
    def respond_user_inactive(self, request, user):
        """
        Called when an inactive user tries to log in.
        Redirect to frontend instead of showing the default template.
        """
        return redirect(f"{FRONTEND_DOMAIN}/auth/login/?error=UserInactive")

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
            raise ImmediateHttpResponse(redirect(f"{FRONTEND_DOMAIN}/auth/login?error=no_email"))

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise ImmediateHttpResponse(redirect(f"{FRONTEND_DOMAIN}/auth/login?error=no_user"))

        if sociallogin.is_existing:
            return

        sociallogin.connect(request, user)
