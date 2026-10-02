from config.settings.components import env_list

from core.utils.ip import trusted_ip_headers_from_env

# Every header listed here must be unconditionally overwritten by a trusted
# proxy: without Cloudflare in front, CF-Connecting-IP has to be removed or a
# client can forge any address and bypass rate limiting. Empty = REMOTE_ADDR only.
TRUSTED_IP_HEADERS = trusted_ip_headers_from_env()

# For example: 'DJANGO_CORS_ORIGIN_WHITELIST=http://localhost:8000'
CORS_ORIGIN_WHITELIST = env_list("DJANGO_CORS_ORIGIN_WHITELIST")
CORS_ALLOWED_ORIGIN_REGEXES = [r"^http://localhost:\d+$"]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
