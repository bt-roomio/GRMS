from typing import cast

from django.contrib.auth.models import Permission

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from core.utils.constants import UI_PERMISSIONS
from users.models import Role


def apply_claims(token, user):
    """Stamp the claims every GRMS token is expected to carry."""
    tenant_id = user.tenant_id

    token["email"] = user.email
    token["tenant_id"] = str(tenant_id) if tenant_id else None
    token["tenant_group_admin"] = bool(user.tenant_group_id)
    token["is_superuser"] = user.is_superuser

    return token


def build_tokens_for(user):
    """
    Issue a claim-carrying token pair outside the login flow.

    Claims are stamped on the refresh token so `TokenRefreshView` copies them onto
    every derived access token instead of quietly dropping them on rotation.
    """
    refresh = cast(RefreshToken, RefreshToken.for_user(user))
    apply_claims(refresh, user)

    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        apply_claims(token, user)

        if user.is_superuser:
            set_perms_superuser(user)

        return token

    def validate(self, attrs):
        email = attrs.get("email")
        if email:
            attrs["email"] = email.lower()
        return super().validate(attrs)


def set_perms_superuser(user):
    role, _ = Role.objects.get_or_create(name="Super user", tenant=None)
    all_permissions = Permission.objects.all()
    role.permissions.add(*all_permissions)
    role.additional_info = {"ui_permissions": UI_PERMISSIONS}
    role.save()

    user.roles.add(role)
    return user
