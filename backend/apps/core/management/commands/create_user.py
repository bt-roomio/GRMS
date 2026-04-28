from django.core.management import BaseCommand

from core.utils.random_letter import get_random_letter
from users.models import User


class Command(BaseCommand):
    def handle(self, **_):
        users_to_create: list[dict[str, str]] = [
            {"email": "bt@room.io", "password": get_random_letter()},
            {"email": "ym@room.io", "password": get_random_letter()},
            {"email": "iy@room.io", "password": get_random_letter()},
            {"email": "cb@room.io", "password": get_random_letter()},
            {"email": "ce@room.io", "password": get_random_letter()},
            {"email": "charalambos@easytech.com.cy", "password": get_random_letter()},
            {"email": "cs@room.io", "password": get_random_letter()},
            {"email": "rk@room.io", "password": get_random_letter()},
            {"email": "ni@room.io", "password": get_random_letter()},
        ]

        for user_data in users_to_create:
            user, created = User.objects.update_or_create(
                email=user_data["email"],
                defaults={
                    "is_active": True,
                    "is_superuser": True,
                    "is_staff": True,
                },
            )
            if created:
                user.set_password(user_data["password"])
                user.save(update_fields=["password"])
                self.stdout.write(f"Created: {user.email} / {user_data['password']}")
            else:
                self.stdout.write(f"Updated: {user.email}")
