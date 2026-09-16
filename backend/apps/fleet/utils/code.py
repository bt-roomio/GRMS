import re
from urllib.parse import urlsplit

from django.conf import settings

MAX_SLUG_LENGTH = 40


def slugify_part(value, fallback: str) -> str:
    """
    Lowercase, underscore-free slug of one part of a node code.

    Underscores are stripped so ``{prefix}_{tenant}_{gateway}`` splits back
    apart unambiguously.
    """
    raw = (value or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return (slug or fallback)[:MAX_SLUG_LENGTH]


def tenant_slug(tenant) -> str:
    return slugify_part(getattr(tenant, "title", None) or str(getattr(tenant, "id", "")), "tenant")


def gateway_slug(gateway) -> str:
    return slugify_part(getattr(gateway, "name", None) or str(getattr(gateway, "id", "")), "gateway")


def node_prefix() -> str:
    """
    This backend's name inside the NetBird account.
    """
    if settings.FLEET_NODE_PREFIX:
        return slugify_part(settings.FLEET_NODE_PREFIX, "roomio")

    domain = settings.FRONTEND_DOMAIN or ""
    if "//" not in domain:
        domain = f"//{domain}"
    host = urlsplit(domain).hostname or ""
    return slugify_part(host.split(".")[0], "roomio")


def build_code(tenant, gateway) -> str:
    """
    Node identifier, also used verbatim as the NetBird hostname.

    Readability and uniqueness only — never a secret.
    """
    return f"{node_prefix()}_{tenant_slug(tenant)}_{gateway_slug(gateway)}"
