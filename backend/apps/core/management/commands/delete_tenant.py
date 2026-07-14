from getpass import getpass

from django.contrib.auth import authenticate
from django.core.management.base import BaseCommand
from django.db import transaction

from main.models import Tenant


class Command(BaseCommand):
    help = "Delete a Tenant and all associated data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Skip confirmation prompt (use with caution)",
        )

    def handle(self, *args, **options):
        # Get tenant name
        tenant_name = input("Enter the name of the Tenant to delete: ").strip()
        if not tenant_name:
            self.stderr.write(self.style.ERROR("Tenant name cannot be empty"))
            return

        # Get admin credentials for verification
        email = input("Enter your admin email for verification: ").strip()
        password = getpass("Enter your admin password: ").strip()

        if not email or not password:
            self.stderr.write(self.style.ERROR("Email or password cannot be empty"))
            return

        try:
            # Verify admin credentials
            user = authenticate(username=email, password=password)
            if not user:
                self.stderr.write(self.style.ERROR("Invalid credentials"))
                return

            try:
                tenant = Tenant.objects.get(title=tenant_name)
            except Tenant.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Tenant with name '{tenant_name}' does not exist"))
                return

            # Prevent deletion of Default tenant
            if tenant_name.lower() == "default":
                self.stderr.write(self.style.ERROR("Cannot delete the Default tenant"))
                return

            # Show tenant information
            self.stdout.write(self.style.WARNING(f"\nTenant to be deleted: {tenant.title}"))
            self.stdout.write(self.style.WARNING(f"Tenant ID: {tenant.id}"))
            self.stdout.write(self.style.WARNING("All related data will be automatically deleted via CASCADE."))

            # Confirmation
            if not options["confirm"]:
                self.stdout.write(self.style.ERROR("\nWARNING: This action is IRREVERSIBLE!"))
                confirmation = input("Type 'DELETE' to confirm deletion: ").strip()
                if confirmation != "DELETE":
                    self.stdout.write(self.style.SUCCESS("Deletion cancelled"))
                    return

            # Perform deletion in a transaction
            with transaction.atomic():
                # Django will automatically delete all related objects via CASCADE
                tenant.delete()

            self.stdout.write(
                self.style.SUCCESS(f"Successfully deleted Tenant '{tenant_name}' and all associated data")
            )

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {e}"))
