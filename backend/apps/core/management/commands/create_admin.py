from django.core.management import BaseCommand

from users.models import User


class Command(BaseCommand):
    help = "Create or update a superuser"

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)

    def handle(self, *args, **options):
        email = options["email"]
        password = options["password"]

        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                "is_active": True,
                "is_superuser": True,
                "is_staff": True,
            },
        )
        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
            self.stdout.write(f"Created: {user.email} / {password}")
        else:
            self.stdout.write(f"Updated: {user.email}")
