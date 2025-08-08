from _typeshed import Incomplete
from django.contrib.auth.models import AbstractUser

from core.models import BaseModel
from users.querysets.user import UsersManager

class User(AbstractUser, BaseModel):
    email: Incomplete
    additional_info: Incomplete
    phone: Incomplete
    date_joined: Incomplete
    last_login: Incomplete
    tenant: Incomplete
    customer_id: Incomplete
    roles: Incomplete
    username: Incomplete
    USERNAME_FIELD: str
    REQUIRED_FIELDS: Incomplete
    objects: UsersManager
    def save(self, *args, **kwargs) -> None: ...

class ResetPassword(BaseModel):
    key: Incomplete
    user: Incomplete
    expires_at: Incomplete
    def save(self, *args, **kwargs): ...

    class Meta:
        db_table: str

class Role(BaseModel):
    name: Incomplete
    tenant: Incomplete
    permissions: Incomplete
    additional_info: Incomplete
    objects: Incomplete

    class Meta:
        verbose_name: str
        verbose_name_plural: str
        db_table: str
        unique_together: Incomplete
        ordering: Incomplete
