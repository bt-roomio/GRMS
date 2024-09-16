import random
import time
from typing import List

from django.core.management.base import BaseCommand
from django.db.models import Subquery, Window, F, QuerySet
from django.db.models.functions import RowNumber

from main.models import Room, Tenant, Customer


class Command(BaseCommand):
    help = "Playground"

    def handle(self, *args, **options):
        pass
        # fake_customers()
        # remove_duplicate_rows(Customer.objects, ["created_at", "title"])


def remove_duplicate_rows(queryset: QuerySet, columns: List[str]):
    subquery = (
        queryset.annotate(
            row_num=Window(
                expression=RowNumber(), partition_by=[F(column) for column in columns], order_by=F("id").asc()
            )
        )
        .filter(row_num__gt=1)
        .values("id")
    )

    data = queryset.filter(id__in=Subquery(subquery))
    elements = data.values(*columns)
    for row in elements:
        print(row)

    if not data:
        print("No data was found.")
        return

    print("*" * 50)
    print(" " * 10, "This elements will be deleted!")
    print("*" * 50)

    yes_or_no = input("Y/N: ")
    if yes_or_no == "N":
        print("you choose No")
    elif yes_or_no == "Y":
        print(data.delete())
    else:
        print("that is not a answer. sorry...")


def fake_customers():
    tenant = Tenant.objects.first()
    for i in range(100):
        Customer.objects.create(title=f"Title" if i % 5 != 0 else f"Title {i}", tenant=tenant)


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
