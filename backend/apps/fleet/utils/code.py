import re

MAX_SLUG_LENGTH = 40


def slugify_part(value, fallback: str) -> str:
    """
    Lowercase, underscore-free slug of one half of a node code.

    Underscores are stripped so ``{tenant}_{gateway}`` splits back apart
    unambiguously.
    """
    raw = (value or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return (slug or fallback)[:MAX_SLUG_LENGTH]


def tenant_slug(tenant) -> str:
    return slugify_part(getattr(tenant, "title", None) or str(getattr(tenant, "id", "")), "tenant")


def gateway_slug(gateway) -> str:
    return slugify_part(getattr(gateway, "name", None) or str(getattr(gateway, "id", "")), "gateway")


def build_code(tenant, gateway) -> str:
    """
    Node identifier, also used verbatim as the NetBird hostname.

    Readability and uniqueness only — never a secret.
    """
    return f"{tenant_slug(tenant)}_{gateway_slug(gateway)}"
