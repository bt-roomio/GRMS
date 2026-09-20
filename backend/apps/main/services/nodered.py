"""
Per-tenant Node-RED: a DNS record, an env file and a compose project on the host.

The same compose invocation as `make nodered-*-<slug>` in deploy/Makefile, so a
provisioned instance can still be managed by hand. Runs in celery-low, the only
worker with the Docker socket and deploy/ mounted.
"""

import logging
import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from core.utils.cloudflare import CloudflareClient
from fleet.utils.code import domain_host, frontend_host, tenant_slug
from main.models import Tenant

logger = logging.getLogger(__name__)

COMPOSE_FILE = "docker-compose.nodered.yml"
ENV_TEMPLATE = ".env.nodered.example"

PENDING, READY, FAILED = "pending", "ready", "failed"


class NodeRedError(Exception):
    """docker compose answered with a non-zero exit code."""


def env_path(slug: str) -> Path:
    return Path(settings.NODERED_DEPLOY_DIR) / f".env.nodered.{slug}"


def removed_env_path(slug: str) -> Path:
    return Path(settings.NODERED_DEPLOY_DIR) / f".env.nodered.{slug}.removed"


def nodered_base_host() -> str:
    """
    Domain the tenant subdomains hang off.

    NODERED_BASE_DOMAIN when set — it carries every label below the tenant, so
    "nodered.bukhara.cloud" and "bukhara.cloud" are both spelled out in full.
    """
    return domain_host(settings.NODERED_BASE_DOMAIN) or (f"nodered.{frontend_host()}" if frontend_host() else "")


def nodered_host(slug: str) -> str:
    return f"{slug}.{nodered_base_host()}"


def read_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and not key.lstrip().startswith("#"):
            values[key.strip()] = value.strip()
    return values


def resolve_slug(tenant: Tenant) -> str:
    """
    DNS label, compose project and env-file suffix of the tenant's Node-RED.

    `compose down` keeps the volume, so a name once held by another tenant
    (live or removed env file) would hand this hotel someone else's flows —
    such a name gets the tenant id appended.
    """
    slug = tenant_slug(tenant)
    for path in (env_path(slug), removed_env_path(slug)):
        if path.exists() and read_env(path).get("NODERED_TENANT_ID") != str(tenant.id):
            return f"{slug}-{tenant.id.hex[:8]}"
    return slug


def write_env(slug: str, tenant: Tenant, host: str) -> Path:
    """
    Fill .env.nodered.example in, keeping its comments and remaining defaults.
    """
    overrides = {
        "TENANT_NAME": slug,
        "NODERED_TENANT_ID": str(tenant.id),
        "NODERED_VIRTUAL_HOST": host,
    }
    if settings.LETSENCRYPT_EMAIL:
        overrides["LETSENCRYPT_EMAIL"] = settings.LETSENCRYPT_EMAIL

    lines = []
    for line in (Path(settings.NODERED_DEPLOY_DIR) / ENV_TEMPLATE).read_text().splitlines():
        key = line.partition("=")[0].strip()
        if "=" in line and key in overrides:
            line = f"{key}={overrides.pop(key)}"
        lines.append(line)
    lines.extend(f"{key}={value}" for key, value in overrides.items())

    path = env_path(slug)
    # The temporary name must not match `.env.nodered.*`, which the Makefile globs.
    tmp = path.with_name(f".tmp{path.name}")
    tmp.write_text("\n".join(lines) + "\n")
    tmp.chmod(0o600)
    os.replace(tmp, path)
    return path


def compose(slug: str, *args: str) -> None:
    command = [
        "docker",
        "compose",
        "-f",
        str(Path(settings.NODERED_DEPLOY_DIR) / COMPOSE_FILE),
        "--project-name",
        f"nodered-{slug}",
        "--env-file",
        str(env_path(slug)),
        *args,
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=settings.NODERED_COMPOSE_TIMEOUT)
    except subprocess.CalledProcessError as exc:
        raise NodeRedError(f"docker compose {' '.join(args)} failed: {(exc.stderr or '').strip() or exc}") from exc


def save_state(tenant_id, roomio_node_url: str | None = None, **fields) -> None:
    """
    Merge into additional_info under a row lock, so concurrent general settings edits survive.
    """
    with transaction.atomic():
        tenant = Tenant.objects.select_for_update().get(id=tenant_id)
        info = tenant.additional_info or {}
        info["nodered"] = {**info.get("nodered", {}), **fields}
        if roomio_node_url is not None:
            info.setdefault("general_settings", {})["roomio_node_url"] = roomio_node_url
        tenant.additional_info = info
        tenant.save(update_fields=["additional_info", "updated_at"])


def provision_nodered(tenant_id) -> None:
    """
    DNS record → env file → container → roomio_node_url. Every step is idempotent.
    """
    tenant = Tenant.objects.filter(id=tenant_id).first()
    if not tenant:
        logger.warning("Node-RED provisioning skipped: tenant %s no longer exists", tenant_id)
        return

    # A retry keeps the name it was given the first time.
    slug = ((tenant.additional_info or {}).get("nodered") or {}).get("slug") or resolve_slug(tenant)
    host = nodered_host(slug)
    save_state(tenant.id, slug=slug, host=host, status=PENDING, error=None)

    try:
        if not nodered_base_host() or not settings.NODERED_DNS_TARGET:
            raise ImproperlyConfigured(
                "NODERED_BASE_DOMAIN (or FRONTEND_DOMAIN) and NODERED_DNS_TARGET (or API_VIRTUAL_HOST) must be set"
            )

        comment = f"GRMS Node-RED: {tenant.title} ({tenant.id})"[:100]
        record = CloudflareClient().upsert_cname(host, settings.NODERED_DNS_TARGET, comment=comment)
        save_state(tenant.id, dns_record_id=record["id"])

        write_env(slug, tenant, host)
        compose(slug, "up", "-d")
    except Exception as exc:
        save_state(tenant.id, status=FAILED, error=str(exc))
        raise

    save_state(tenant.id, roomio_node_url=f"https://{host}", status=READY, error=None)
    logger.info("Node-RED for tenant %s is up at %s", tenant.id, host)


def deprovision_nodered(slug: str, dns_record_id: str | None = None) -> None:
    """
    Stop the container and drop its DNS record. The volume with the flows stays.
    """
    path = env_path(slug)
    if path.exists():
        compose(slug, "down")
        os.replace(path, removed_env_path(slug))

    client = CloudflareClient()
    if not dns_record_id:
        record = client.find_record(nodered_host(slug))
        dns_record_id = record["id"] if record else None
    if dns_record_id:
        client.delete_record(dns_record_id)

    logger.info("Node-RED %s removed", slug)


def schedule_nodered_provisioning(tenant: Tenant) -> None:
    if not settings.NODERED_PROVISIONING_ENABLED:
        return

    from main.tasks import provision_nodered_task

    tenant_id = str(tenant.id)
    transaction.on_commit(lambda: provision_nodered_task.delay(tenant_id))


def schedule_nodered_teardown(tenant: Tenant) -> None:
    """
    Must be called before the tenant is deleted: the slug lives on the tenant row.
    """
    info = (tenant.additional_info or {}).get("nodered") or {}
    if not settings.NODERED_PROVISIONING_ENABLED or not info.get("slug"):
        return

    from main.tasks import deprovision_nodered_task

    slug, dns_record_id = info["slug"], info.get("dns_record_id")
    transaction.on_commit(lambda: deprovision_nodered_task.delay(slug, dns_record_id))
