import random
import time

from django.core.management.base import BaseCommand

from main.models import Customer, Room, Tenant


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        pass


def fake_customers():
    tenant = Tenant.objects.first()
    tt = int(time.time())
    data = []
    for i in range(100):
        if i % 3 == 0:
            tt = int(time.time()) + i
        data.append(Customer(title=f"Title" if i % 5 != 0 else f"Title {i}", tenant=tenant, created_at=tt))

    Customer.objects.bulk_create(data)


def fake_rooms():
    tenants = Tenant.objects.all()
    for i in range(5000):
        r = Room.objects.get_or_create(
            number=random.randint(1, 100),
            floor=random.randint(1, 100),
            block=random.randint(1, 100),
            state=random.choice([x[0] for x in Room.STATE]),
            tenant=random.choice(tenants),
            status=random.choice([x[0] for x in Room.STATUS]),
            created_at=random.choice([int(time.time()), int(time.time() - (86500 * 1.5))]),
        )
        print(r)
