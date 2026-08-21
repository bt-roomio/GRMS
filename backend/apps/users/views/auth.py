from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from users.serializers.jwt_token import build_tokens_for

FRONTEND_DOMAIN = settings.FRONTEND_DOMAIN


@login_required
def callback_provider(request):
    user = request.user
    social_accounts = SocialAccount.objects.filter(user=user)

    social_account = social_accounts.first()

    if not social_account:
        return redirect(f"{FRONTEND_DOMAIN}/auth/login/?error=NoSocialAccount")

    tokens = build_tokens_for(user)
    response = redirect(f"{FRONTEND_DOMAIN}/auth/login/?access={tokens['access']}&refresh={tokens['refresh']}")
    response.delete_cookie("sessionid", path="/")
    response.delete_cookie("messages", path="/")
    return response
