import os

AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "core.utils.backends.CustomBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

FRONTEND_DOMAIN = os.getenv("FRONTEND_DOMAIN", "http://localhost:5173")

# allauth account configuration for email-only user model (no username field)
SITE_ID = 1
ACCOUNT_ADAPTER = "users.auth.adapters.NoSignupAccountAdapter"
SOCIALACCOUNT_ADAPTER = "users.auth.adapters.NoNewSocialSignupAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_QUERY_EMAIL = True
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

LOGIN_REDIRECT_URL = FRONTEND_DOMAIN
LOGOUT_REDIRECT_URL = "/admin"

# Keycloak SSO goes through our own views (users.views.keycloak), not allauth.
KC_BASE_URL = os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080")
KC_REALM = os.getenv("KEYCLOAK_REALM", "realm_name")
KC_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "client_id")
KC_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "")

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": [
            {
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "key": "",
                "sites": [SITE_ID],
            }
        ],
        "SCOPE": ["openid", "email", "profile"],
        "AUTH_PARAMS": {"prompt": "select_account"},
        "FETCH_USERINFO": True,
    },
    "microsoft": {
        "SCOPE": ["openid", "email", "profile", "offline_access", "User.Read"],
        "AUTH_PARAMS": {"prompt": "select_account"},
        "FETCH_USERINFO": True,
        "APPS": [
            {
                "provider_id": "microsoft",
                "name": "Microsoft",
                "client_id": os.getenv("MS_CLIENT_ID", ""),
                "secret": os.getenv("MS_CLIENT_SECRET", ""),
                "sites": [SITE_ID],
            }
        ],
    },
}
