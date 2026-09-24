import logging

from admin_panel.swagger.brute_force import AdminUnlockUserSwagger
from admin_panel.utils.scope import get_scoped_user_or_404

from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.brute_force import unlock_account
from core.utils.permission import check_perms

logger = logging.getLogger("security")


class AdminUserLockView(APIView):
    """
    Lift an account lockout caused by wrong passwords.

    Access: anyone holding `main.unlock_user` (superusers have it implicitly).
    The scope is enforced by `get_scoped_user_or_404`: a regular user reaches
    only the staff of their own hotel, a chain admin only accounts of their own
    chain, and everything else is a 404, so the caller never learns those
    accounts exist.
    """

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminUnlockUserSwagger,
        security=[{"Bearer": []}],
        operation_description=(
            "**Requires `main.unlock_user`.** Clears the brute force counters for an account: failed attempt "
            "counters, lockout, progressive delay and extended windows across all protected "
            "endpoints. A permanent IP ban (hard block) is not affected."
        ),
    )
    @check_perms(["main.unlock_user"])
    def post(self, request, user_id):
        user = get_scoped_user_or_404(request, user_id)
        result = unlock_account(user.email)

        logger.warning(
            f"Account unlocked: {user.email} (by {request.user.email}, "
            f"ips={result['cleared_ips']}, keys={result['cleared_keys']})"
        )

        return Response({"message": "Account unlocked.", **result})
