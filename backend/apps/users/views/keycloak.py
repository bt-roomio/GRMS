import base64
import hashlib
import os
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect, JsonResponse

from rest_framework_simplejwt.tokens import RefreshToken

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
    resp.set_cookie("kc_state", state, samesite="Lax")
    resp.set_cookie("kc_nonce", nonce, samesite="Lax")
    resp.set_cookie("kc_cv", code_verifier, samesite="Lax")
    return resp


def kc_callback(request):
    state_cookie = request.GET.get("kc_state")
    code_verifier = request.GET.get("kc_cv")
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
    tokens.get("id_token")
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
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({"detail": "User not allowed"}, status=403)

    refresh = RefreshToken.for_user(user)
    payload = {"access": str(refresh.access_token), "refresh": str(refresh)}  # pyright: ignore

    return JsonResponse(payload, status=200)
