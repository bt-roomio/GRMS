from django.core.management.base import BaseCommand

from users.models import Role


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        roles = [{**i, "id": str(i["id"])} for i in Role.objects.all().values()]
        print(roles)
