from getpass import getpass
from uuid import UUID

from django.core.management.base import BaseCommand
from django.db.models import Q

from main.models import TenantGroup
from main.services.tenant_provisioning import provision_tenant
from users.models import User


class Command(BaseCommand):
    help = "Create a Tenant and an Admin User"

    def add_arguments(self, parser):
        parser.add_argument(
            "--group",
            help="Attach the tenant to an existing hotel chain (id or title)",
        )

    def resolve_group(self, value):
        if not value:
            return None

        lookup = Q(title__iexact=value)
        try:
            lookup |= Q(pk=UUID(value))
        except ValueError:
            pass  # not a uuid, match by title only

        group = TenantGroup.objects.filter(lookup).first()
        if not group:
            raise ValueError(f"Tenant group '{value}' not found")
        return group

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
            group = self.resolve_group(options.get("group"))
            tenant = provision_tenant(title=title, email=email, password=password, group=group)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {e}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Successfully created Tenant: {tenant} and Admin: {email}"))
