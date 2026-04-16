from django.contrib.auth.models import Permission

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.utils.constants import UI_PERMISSIONS
from users.models import Role


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["email"] = user.email
        token["tenant_id"] = str(user.tenant_id) if user.tenant_id else None
        token["is_superuser"] = user.is_superuser
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
