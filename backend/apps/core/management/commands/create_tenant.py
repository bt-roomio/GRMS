from getpass import getpass

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.db import transaction

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
                role.additional_info = {
                    "ui_permissions": ["main", "overview", "energy", "rooms", "r-status", "r-available", "r-checkin",
                                       "r-occupied", "r-dnd", "r-makeup", "r-offline", "r-read", "r-actions",
                                       "r-act-checkin", "r-act-checkout", "r-act-makeup", "r-act-dnd", "r-print",
                                       "room-inner", "ri-controls", "ri-cards", "ri-card-add", "ri-card-active",
                                       "ri-card-active-read", "ri-card-act", "ri-card-disconnect", "ri-card-logs",
                                       "ri-guests", "ri-guest-read", "ri-guest-actions", "ri-guest-checkin",
                                       "ri-guest-checkouts", "ri-guest-moveall", "ri-guest-act", "ri-guest-checkout",
                                       "ri-guest-move", "public-spaces", "public-spaces-read", "public-space-inner",
                                       "scenario", "access", "a-groups", "a-staff", "a-staff-read", "a-staff-editor",
                                       "a-staff-add", "a-staff-edit", "a-staff-info", "a-staff-del", "a-staff-card",
                                       "a-group-mgmt", "a-group-read", "a-group-editor", "a-group-add", "a-group-edit",
                                       "a-group-del", "a-group-info", "a-cards", "a-card-read", "a-card-sync",
                                       "a-card-search", "a-card-del", "config", "c-dash", "c-dash-read",
                                       "c-dash-editor", "c-dash-import", "c-dash-export", "c-dash-add", "c-dash-edit",
                                       "c-dash-copy", "c-dash-del", "c-dash-inner", "c-dash-i-read", "c-dash-i-editor",
                                       "c-dash-alias", "c-dash-widget-add", "c-dash-widget-edit", "c-dash-widget-del",
                                       "c-users", "c-user-read", "c-user-editor", "c-user-add", "c-user-edit",
                                       "c-user-del", "c-user-act", "c-user-resend", "c-user-demo", "c-roles",
                                       "c-role-read", "c-role-editor", "c-role-add", "c-role-edit", "c-role-del",
                                       "c-role-copy", "c-role-import", "c-role-export", "c-pubspace", "c-pub-read",
                                       "c-pub-editor", "c-pub-add", "c-pub-edit", "c-pub-del", "c-rooms", "c-room-read",
                                       "c-room-editor", "c-room-add", "c-room-edit", "c-room-del", "c-room-import",
                                       "c-room-export", "c-roomtypes", "c-rtype-read", "c-rtype-editor", "c-rtype-add",
                                       "c-rtype-edit", "c-rtype-del", "c-devices", "c-dev-read", "c-dev-editor",
                                       "c-dev-edit", "c-dev-del", "c-dev-info", "c-devprofile", "c-devp-read",
                                       "c-devp-editor", "c-devp-add", "c-devp-edit", "c-devp-del", "c-gateway",
                                       "c-gw-read", "c-gw-editor", "c-gw-add", "c-gw-edit", "c-gw-del", "c-gw-info",
                                       "c-gw-conn", "c-conn-read", "c-conn-editor", "c-conn-add", "c-conn-del",
                                       "c-conn-logs", "c-conn-import", "c-conn-export", "c-conn-inner", "c-conn-gen",
                                       "c-conn-gen-read", "c-conn-gen-edit", "c-conn-srv", "c-conn-srv-read",
                                       "c-conn-srv-edit", "c-conn-addr", "c-addr-read", "c-addr-editor",
                                       "c-addr-import", "c-addr-export", "c-addr-add", "c-addr-del", "c-addr-copy",
                                       "c-addr-edit", "c-conn-devs", "c-cdev-read", "c-cdev-editor", "c-cdev-add",
                                       "c-cdev-del", "c-cdev-fw", "c-cdev-boot", "c-cdev-config", "c-cdev-files",
                                       "c-cdev-reset", "c-cdev-scan", "c-cdev-sync", "c-conn-config", "c-cconfig-read",
                                       "c-cconfig-editor", "c-cconfig-edit", "c-cconfig-import", "c-cconfig-export",
                                       "c-cconfig-init", "settings", "s-general", "s-gen-general", "s-gen-read",
                                       "s-gen-edit", "s-gen-email", "s-gen-email-read", "s-gen-email-edit",
                                       "s-gen-alarms", "s-gen-alarms-read", "s-gen-alarms-edit", "s-integration",
                                       "s-int-read", "s-int-edit", "global-settings"]}
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
