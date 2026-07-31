import logging

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from fleet.enroll import (
    EnrollmentError,
    consume_token,
    render_bootstrap,
    verify_install_token,
)
from fleet.models import FleetAuditLog, FleetNode
from fleet.utils.audit import client_ip, log_action

logger = logging.getLogger(__name__)


def _plain(body, status=200):
    response = HttpResponse(body, status=status, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "no-store"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@method_decorator(csrf_exempt, name="dispatch")
class InstallScriptView(View):
    """
    Public endpoint behind the `curl ... | sudo bash` one-liner.

    Unauthenticated by design: the machine being enrolled has no credentials
    yet. The one-time token is the whole of the security, so every failure
    returns the same 410 and leaks nothing.
    """

    def get(self, request, code):
        if not settings.FLEET_SSH_PUBLIC_KEY or not settings.NETBIRD_MANAGEMENT_URL:
            logger.error("Install requested for %s but fleet enrollment is not configured", code)
            return _plain("Fleet enrollment is not configured on this server.\n", status=503)

        token = request.GET.get("t", "")
        node = None

        try:
            with transaction.atomic():
                node = FleetNode.objects.select_for_update().filter(code=code, is_active=True).first()
                if node is None:
                    raise EnrollmentError("unknown node")

                verify_install_token(node, token)

                # Render first, then burn: `consume_token` wipes the plaintext.
                # The row is locked, so concurrent fetches cannot both succeed.
                script = render_bootstrap(node, node.netbird_setup_key)
                consume_token(node)
        except EnrollmentError as exc:
            log_action(
                FleetAuditLog.ACTION.BOOTSTRAP_REJECTED,
                node=node,
                detail={"code": code, "reason": str(exc)},
                remote_addr=client_ip(request),
            )
            return _plain("This install link is invalid, expired or already used.\n", status=410)

        log_action(
            FleetAuditLog.ACTION.BOOTSTRAP_SERVED,
            node=node,
            detail={"code": node.code},
            remote_addr=client_ip(request),
        )
        return _plain(script)
