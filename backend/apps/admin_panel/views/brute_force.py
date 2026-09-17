import logging

from admin_panel.swagger.brute_force import AdminUnlockUserSwagger, AdminUserLockStatusSwagger
from admin_panel.utils.scope import get_scoped_user_or_404

from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.brute_force import get_lock_status, unlock_account
from core.utils.permission import IsSuperUser

logger = logging.getLogger("security")


class AdminUserLockView(APIView):
    """
    Inspect and lift an account lockout caused by wrong passwords.

    Access: SYS_ADMIN (superuser) and TENANT_GROUP_ADMIN (a superuser pinned to a
    chain through `tenant_group_id`). The scope is enforced by
    `get_scoped_user_or_404`: a chain admin only reaches accounts of their own
    chain and gets a 404 for the rest, so they never learn those accounts exist.
    """

    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminUserLockStatusSwagger,
        security=[{"Bearer": []}],
        operation_description=(
            "**Superuser only.** Returns the brute force lock status of an account: "
            "whether it is locked out after failed logins, from which IPs, and for how long."
        ),
    )
    def get(self, request, user_id):
        user = get_scoped_user_or_404(request, user_id)
        return Response(get_lock_status(user.email))

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminUnlockUserSwagger,
        security=[{"Bearer": []}],
        operation_description=(
            "**Superuser only.** Clears the brute force counters for an account: failed attempt "
            "counters, lockout, progressive delay and extended windows across all protected "
            "endpoints. A permanent IP ban (hard block) is not affected."
        ),
    )
    def post(self, request, user_id):
        user = get_scoped_user_or_404(request, user_id)
        result = unlock_account(user.email)

        logger.warning(
            f"Account unlocked by admin: {user.email} (by {request.user.email}, "
            f"ips={result['cleared_ips']}, keys={result['cleared_keys']})"
        )

        return Response({"message": "Account unlocked.", **result})
