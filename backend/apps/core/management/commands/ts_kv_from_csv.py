import csv
from datetime import datetime, timedelta

import pytz
from django.core.management.base import BaseCommand
from django.db.models import Q

from shuttle.models import TsKvDictionary


class Command(BaseCommand):
    help = "Save ts_kv from csv file"

    def handle(self, *args, **options):
        key_ids = TsKvDictionary.objects.filter(
            Q(key__endswith="_LOGS") | Q(key__contains="Events") | Q(key__contains="ERRORS")
        ).values_list("key_id", flat=True)
        csv_path = "/Users/bakhodir/Desktop/backup_ts_kv.csv"
        count_third_column_values(csv_path, key_ids)


def count_third_column_values(csv_file_path, key_ids):
    cleaned_rows = []
    with open(csv_file_path, newline="") as csvfile:
        reader = csv.reader(csvfile)
        # count = 0
        now = datetime.now(pytz.UTC)

        for row in reader:
            # if count >= 100:
            #     break

            if len(row) >= 3 and row[2].strip().isdigit():
                key_id = int(row[2])
                if key_id in key_ids:
                    dt = datetime.fromisoformat(row[1])
                    grt = now - dt > timedelta(days=7)
                    if grt:
                        print("Ignored row: ", row)
                        continue

                    cleaned_rows.append(row[1:])
                    continue

            cleaned_rows.append(row[1:])

            # count += 1

    print(len(cleaned_rows))

    with open("/Users/bakhodir/Desktop/backup_ts_kv_cleaned.csv", mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile, lineterminator="\n")
        writer.writerows(cleaned_rows)
