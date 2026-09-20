import os

# Per-tenant Node-RED — see `main.services.nodered`.
# Off by default: provisioning creates public DNS records and containers on the host.
NODERED_PROVISIONING_ENABLED = os.getenv("NODERED_PROVISIONING_ENABLED", "False").lower() in ("true", "1", "yes")

# Domain the tenant subdomains hang off: <tenant>.<NODERED_BASE_DOMAIN>.
# Empty falls back to nodered.<FRONTEND_DOMAIN host>.
NODERED_BASE_DOMAIN = os.getenv("NODERED_BASE_DOMAIN", "")
# Where celery-low sees deploy/ (docker-compose.nodered.yml, .env.nodered.*).
NODERED_DEPLOY_DIR = os.getenv("NODERED_DEPLOY_DIR", "/deploy")
# CNAME target of every tenant subdomain — the host nginx-proxy listens on.
NODERED_DNS_TARGET = os.getenv("NODERED_DNS_TARGET", "") or os.getenv("API_VIRTUAL_HOST", "")
# `up -d` may pull the image, hence the generous limit.
NODERED_COMPOSE_TIMEOUT = float(os.getenv("NODERED_COMPOSE_TIMEOUT", "540"))
LETSENCRYPT_EMAIL = os.getenv("LETSENCRYPT_EMAIL", "")

CLOUDFLARE_API_URL = "https://api.cloudflare.com/client/v4"
# API token with Zone.DNS:Edit on the zone below.
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "")
CLOUDFLARE_TIMEOUT = float(os.getenv("CLOUDFLARE_TIMEOUT", "10"))
