import uuid

from django.contrib.auth.models import AbstractUser, Permission
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel
from core.utils.unix_timestamp import UnixTimeStampField
from users.querysets.role import RoleQuerySet
from users.querysets.user import UsersManager
from users.utils import tokens
from users.utils.fields import expires_hour


class User(AbstractUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique identifier for the user"),
    )
    email = models.EmailField(
        help_text=_("Email address used for authentication and communication"),
    )
    additional_info = models.JSONField(
        blank=True,
        null=True,
        help_text=_("Additional user information stored as JSON"),
    )
    phone = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("User's phone number"),
    )
    tenant = models.ForeignKey(
        "main.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=_("The tenant (hotel/property) this user belongs to"),
    )
    customer_id = models.ForeignKey(
        "main.Customer",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=_("Customer associated with this user"),
    )
    roles = models.ManyToManyField(
        "users.Role",
        verbose_name=_("roles"),
        blank=True,
        help_text=_("The roles this user belongs to. A user will get all permissions granted to each of their roles."),
        related_name="user_set",
        related_query_name="user",
    )

    username = None
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UsersManager()

    # TODO: optimise
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    class Meta:
        db_table = "users_users"
        default_related_name = "users"
        constraints = [
            UniqueConstraint(
                Lower("email"),
                condition=Q(is_active=True),
                name="unique_user_email_is_active",
            ),
        ]


class ResetPassword(BaseModel):
    key = models.CharField(
        max_length=40,
        unique=True,
        help_text=_("Unique token for password reset"),
    )
    user = models.ForeignKey(
        User,
        models.CASCADE,
        help_text=_("User who requested the password reset"),
    )
    expires_at = UnixTimeStampField(
        default=expires_hour,
        help_text=_("Unix timestamp when the reset token expires"),
    )

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = tokens.generate()
        return super(ResetPassword, self).save(*args, **kwargs)

    def __str__(self):
        return self.key

    class Meta(BaseModel.Meta):
        db_table = "users_reset_password"


class Role(BaseModel):
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the role"),
    )
    tenant = models.ForeignKey(
        "main.Tenant",
        models.CASCADE,
        related_name="roles",
        help_text=_("Tenant (hotel/property) this role belongs to"),
    )
    permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("permissions"),
        blank=True,
        help_text=_("Specific permissions granted to this role"),
    )
    additional_info = models.JSONField(
        blank=True,
        null=True,
        help_text=_("Additional role configuration stored as JSON"),
    )

    objects = RoleQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        verbose_name = "role"
        verbose_name_plural = "roles"
        db_table = "users_roles"
        unique_together = (("name", "tenant"),)
        ordering = ("-created_at",)

    def __str__(self):
        return self.name
