from django.core.management.base import BaseCommand

from users.models import User
from users.utils.emails import send_reset_link_email


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        user = User.objects.get(email='akanematullo@gmail.com')
        send_reset_link_email(user)
        return "hello"
