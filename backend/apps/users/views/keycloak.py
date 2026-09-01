import base64
import hashlib
import os
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect

from users.serializers.jwt_token import build_tokens_for

KC_BASE = settings.KC_BASE_URL
KC_REALM = settings.KC_REALM
KC_CLIENT_ID = settings.KC_CLIENT_ID
KC_CLIENT_SECRET = settings.KC_CLIENT_SECRET or None
REDIRECT_URI = f"{settings.FRONTEND_DOMAIN}/auth/login"


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def kc_begin(request):
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    code_verifier = _b64url(os.urandom(32))
    code_challenge = _b64url(hashlib.sha256(code_verifier.encode()).digest())

    # Сохраним в HttpOnly cookies
    resp = HttpResponseRedirect(
        f"{KC_BASE}/realms/{KC_REALM}/protocol/openid-connect/auth?"
        + urlencode(
            {
                "client_id": KC_CLIENT_ID,
                "response_type": "code",
                "redirect_uri": REDIRECT_URI,
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                # "prompt": "login", # опционально
            }
        )
    )
    resp.set_cookie("kc_state", state, httponly=True, samesite="Lax")
    resp.set_cookie("kc_nonce", nonce, httponly=True, samesite="Lax")
    resp.set_cookie("kc_cv", code_verifier, httponly=True, samesite="Lax")
    return resp


def kc_callback(request):
    state_cookie = request.COOKIES.get("kc_state")
    code_verifier = request.COOKIES.get("kc_cv")
    state_q = request.GET.get("state")
    code = request.GET.get("code")

    if not state_cookie or state_q != state_cookie or not code or not code_verifier:
        return JsonResponse({"detail": "Invalid state or code"}, status=400)
    token_url = f"{KC_BASE}/realms/{KC_REALM}/protocol/openid-connect/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": KC_CLIENT_ID,
        "code_verifier": code_verifier,
    }
    if KC_CLIENT_SECRET:
        data["client_secret"] = KC_CLIENT_SECRET

    r = requests.post(token_url, data=data, timeout=10)
    if r.status_code != 200:
        return JsonResponse({"detail": "Token exchange failed", "body": r.text}, status=400)

    tokens = r.json()
    id_token = tokens.get("id_token")
    access_token = tokens.get("access_token")

    ui = requests.get(
        f"{KC_BASE}/realms/{KC_REALM}/protocol/openid-connect/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    ).json()
    email = ui.get("email")
    if not email:
        return JsonResponse({"detail": "No email from Keycloak"}, status=400)

    User = get_user_model()
    try:
        user = User.objects.get(email=email, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({"detail": "User not allowed"}, status=403)

    payload = {**build_tokens_for(user), "id_token": id_token}
    return JsonResponse(payload, status=200)


def kc_logout(request):
    id_token = request.COOKIES.get("kc_id_token")
    # чистим свои JWT-куки
    resp = redirect(REDIRECT_URI)
    resp.delete_cookie("access")
    resp.delete_cookie("refresh")
    resp.delete_cookie("kc_id_token")

    if not id_token:
        return resp

    logout_url = (
        f"{KC_BASE}/realms/{KC_REALM}/protocol/openid-connect/logout"
        f"?id_token_hint={id_token}"
        f"&post_logout_redirect_uri={REDIRECT_URI}"
        f"&client_id={KC_CLIENT_ID}"
    )
    return redirect(logout_url)
