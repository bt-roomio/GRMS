from django.contrib.auth.base_user import BaseUserManager
from django.db.models import F, Q


class UsersManager(BaseUserManager):
    """
    Custom user model manager that supports using email instead of username.
    """

    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: username, "is_active": True})

    def list(self, tenant_id, sort_by=None, search_field=None, search_value=None):
        # `tenant_id=None` would match every hotel-less account (chain admins, superusers)
        # instead of returning nothing, so an empty scope is spelled out explicitly.
        if not tenant_id:
            return self.none()

        query = self.prefetch_related("roles").filter(tenant_id=tenant_id, is_active=True)

        if sort_by:
            # INFO: nulls_last() in asc or desc can't help, we need sort empty fields
            fields = []
            for field in sort_by:
                dash = field.startswith("-")
                field = field.replace("-", "")

                query = query.exclude(first_name="") if field == "first_name" else query

                field = F(field).desc() if dash else F(field).asc()
                fields.append(field)
            query = query.order_by(*fields)

        if search_field and search_value:
            query = query.filter(Q(**{f"{search_field}__icontains": search_value}))
        elif search_value:
            query = query.filter(
                Q(first_name__icontains=search_value)
                | Q(last_name__icontains=search_value)
                | Q(email__icontains=search_value)
            )

        return query

    def create_user(self, email, password, **extra_fields):
        """
        Creates and saves a User with the given email and password
        """
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Creates and saves a superuser with the given email and password
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)
