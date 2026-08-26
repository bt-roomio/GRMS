from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission


class CustomBackend(ModelBackend):
    """Permissions come from `users.Role` rather than Django groups."""

    def _get_group_permissions(self, user_obj, obj=None):
        user_roles_field = get_user_model()._meta.get_field("roles")
        user_roles_query = f"role__{user_roles_field.related_query_name()}"
        return Permission.objects.filter(**{user_roles_query: user_obj})
