import time

from core.models import BaseModel
from core.utils.unix_timestamp import UnixTimeStampField
from django.contrib.auth.models import AbstractUser
from django.db import models
from users.querysets.user import UsersManager
from users.utils import tokens
from users.utils.fields import expires_hour


class User(AbstractUser, BaseModel):
    email = models.EmailField(unique=True)
    additional_info = models.JSONField(blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    date_joined = models.BigIntegerField(default=time.time, editable=False)
    last_login = UnixTimeStampField(default=time.time, blank=True, null=True)
    tenant = models.ForeignKey("main.Tenant", on_delete=models.CASCADE, null=True, blank=True)
    customer_id = models.ForeignKey("main.Customer", on_delete=models.CASCADE, null=True, blank=True)

    username = None
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UsersManager()

    class Meta(AbstractUser.Meta):
        db_table = "users_users"
        default_related_name = "users"


class ResetPassword(BaseModel):
    key = models.CharField(max_length=40, unique=True)
    user = models.ForeignKey(User, models.CASCADE)
    expires_at = UnixTimeStampField(default=expires_hour)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = tokens.generate()
        return super(ResetPassword, self).save(*args, **kwargs)

    def __str__(self):
        return self.key

    class Meta:
        db_table = "users_reset_password"
