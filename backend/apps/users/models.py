import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from users.querysets.user import UsersManager


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    additional_info = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False, null=True)
    # enabled = models.BooleanField(blank=True, null=True)
    # reset_token = models.CharField(unique=True, max_length=255, blank=True, null=True)
    # activate_token = models.CharField(unique=True, max_length=255, blank=True, null=True)
    # tenant_id = models.UUIDField(blank=True, null=True)
    # customer_id = models.UUIDField(blank=True, null=True)

    username = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UsersManager()

    class Meta(AbstractUser.Meta):
        db_table = 'users_users'
        default_related_name = 'users'
