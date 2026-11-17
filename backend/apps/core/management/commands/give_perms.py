from django.core.management.base import BaseCommand

from users.models import Role


class Command(BaseCommand):
    help = "Grant all permissions to all tenant admins"

    def handle(self, *args, **options):
        Role.objects.admins().grant_all_permissions()
