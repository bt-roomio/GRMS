import logging

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView, Response

from core.utils.permission import check_perms
from fleet.models import FleetAuditLog, FleetNode
from fleet.netbird.exceptions import NetBirdError
from fleet.swagger.enrollment import install_swagger
from fleet.utils.audit import client_ip, log_action
from fleet.utils.enroll import (
    EnrollmentError,
    consume_token,
    install_command,
    install_url,
    prepare_enrollment,
    render_bootstrap,
    verify_install_token,
)
from fleet.utils.scope import tenant_scope

logger = logging.getLogger(__name__)


def _plain(body, status=200):
    response = HttpResponse(body, status=status, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "no-store"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


class FleetNodeInstallView(APIView):
    """
    Everything behind the "Install agent" button.

    Whatever the node had before, it comes out with exactly one unused
    single-use setup key and no peer.
    """

    @install_swagger()
    @check_perms(["fleet.enroll_fleetnode"])
    def post(self, request, pk):
        node = FleetNode.objects.get_node(pk, tenant_scope(request))
        replaced = bool(node.netbird_peer_id or node.netbird_setup_key_id)

        try:
            # The key never leaves the server; it is rendered into the script
            # when the install link is fetched.
            prepare_enrollment(node, user=request.user)
        except NetBirdError as exc:
            logger.exception("Could not prepare enrollment for %s", node.code)
            raise ValidationError({"netbird": str(exc)}) from exc
        except EnrollmentError as exc:
            raise ValidationError({"netbird": str(exc)}) from exc

        return Response(
            {
                "install_url": install_url(node, request),
                "command": install_command(node, request),
                "hostname": node.code,
                "peer_replaced": replaced,
                "expires_at": node.token_expires_at,
            }
        )


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
