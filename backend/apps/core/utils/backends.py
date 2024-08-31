from django.contrib.auth import get_user_model

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission


class CustomBackend(ModelBackend):
    def _get_group_permissions(self, user_obj, obj=None):
        user_groups_field = get_user_model()._meta.get_field("roles")
        user_groups_query = "role__%s" % user_groups_field.related_query_name()
        return Permission.objects.filter(**{user_groups_query: user_obj})
