from getpass import getpass

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from core.utils.constants import UI_PERMISSIONS
from main.models import DeviceProfile, Tenant, TenantProfile
from users.models import Role, User


class Command(BaseCommand):
    help = "Create a Tenant and an Admin User"

    def handle(self, *args, **options):
        title = input("Enter the title for the new Tenant: ").strip()
        if not title:
            self.stderr.write(self.style.ERROR("Title cannot be empty"))
            return

        email = input("Enter the email for the new Admin: ").strip()
        password = getpass("Enter the password for the new Admin: ").strip()

        if not email or not password:
            self.stderr.write(self.style.ERROR("Email or password cannot be empty"))
            return

        if User.objects.filter(email=email).exists():
            self.stderr.write(self.style.ERROR(f"User with email '{email}' already exists"))
            return

        try:
            with transaction.atomic():
                tenant_profile, _ = TenantProfile.objects.get_or_create(name="Default", defaults={"is_default": True})
                new_tenant, created = Tenant.objects.get_or_create(tenant_profile=tenant_profile, title=title)
                Tenant.objects.get_or_create(tenant_profile=tenant_profile, title="Default")

                role, _ = Role.objects.get_or_create(name="TENANT_ADMIN", tenant=new_tenant)
                all_permissions = Permission.objects.all()
                role.permissions.add(*all_permissions)
                role.additional_info = {"ui_permissions": UI_PERMISSIONS}
                role.save()

                if not created:
                    self.stdout.write(self.style.WARNING(f"Tenant with title '{title}' already exists."))

                user = User.objects.create(tenant=new_tenant, email=email, password=make_password(password))
                user.roles.add(role)

                for name in ["Default", "Integration Devices", "Card Reader"]:
                    DeviceProfile.objects.get_or_create(name=name, tenant=new_tenant, type="DEFAULT")

            self.stdout.write(self.style.SUCCESS(f"Successfully created Tenant: {new_tenant} and User: {user}"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {e}"))
