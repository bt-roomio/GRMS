from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from rest_framework_simplejwt.tokens import RefreshToken

FRONTEND_DOMAIN = settings.FRONTEND_DOMAIN


@login_required
def callback_provider(request):
    user = request.user
    social_accounts = SocialAccount.objects.filter(user=user)

    social_account = social_accounts.first()

    if not social_account:
        return redirect(f"{FRONTEND_DOMAIN}/auth/login/?error=NoSocialAccount")

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)  # pyright: ignore
    refresh_token = str(refresh)
    response = redirect(f"{FRONTEND_DOMAIN}/auth/login/?access={access_token}&refresh={refresh_token}")
    response.delete_cookie("sessionid", path="/")
    response.delete_cookie("messages", path="/")
    return response
