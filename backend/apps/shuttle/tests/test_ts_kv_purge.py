from datetime import timedelta

from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone

from shuttle.models import TsKv, TsKvDictionary
from shuttle.services.ts_kv_purge import purge_ts_kv_keys

DEVICE_ID = "47aef21b-6cc9-4ec5-8573-1a6f491940c0"


@override_settings(TSKV_PURGE_KEYS=["*_LOGS"], TSKV_PURGE_AFTER_DAYS=30)
class TsKvPurgeTest(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.log_key = TsKvDictionary.objects.create(key="PURGE_TEST_LOGS")
        self.telemetry_key = TsKvDictionary.objects.create(key="purge_test_temperature")

    def add_day(self, days_ago: int):
        """A few rows of both keys in the middle of the day `days_ago` days back."""
        base = self.now - timedelta(days=days_ago)
        TsKv.objects.bulk_create(
            TsKv(ts=base + timedelta(minutes=minute), entity_id=DEVICE_ID, key=key, str_v="line", long_v=minute)
            for minute in range(10)
            for key in (self.log_key, self.telemetry_key)
        )

    def count(self, key, days_ago: int) -> int:
        base = self.now - timedelta(days=days_ago)
        return TsKv.objects.filter(key=key, ts__gte=base, ts__lt=base + timedelta(minutes=10)).count()

    def compress_old_chunks(self):
        with connection.cursor() as cursor:
            # The test inserts and compresses in one transaction: fire the deferred FK checks
            # before compression moves the rows, or they fail at teardown.
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cursor.execute(
                "SELECT compress_chunk(c, if_not_compressed => true) "
                "FROM show_chunks('shuttle_ts_kv', older_than => now() - interval '31 days') c"
            )

    def partially_compressed_chunks(self) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM _timescaledb_catalog.chunk c "
                "JOIN _timescaledb_catalog.hypertable h ON h.id = c.hypertable_id "
                "WHERE h.table_name = 'shuttle_ts_kv' AND c.status & 8 = 8"
            )
            return cursor.fetchone()[0]

    def test_deletes_matched_keys_from_compressed_chunks_only(self):
        self.add_day(33)
        self.add_day(2)
        self.compress_old_chunks()

        deleted = purge_ts_kv_keys()

        self.assertEqual(deleted, 10)
        self.assertEqual(self.count(self.log_key, 33), 0)
        self.assertEqual(self.count(self.telemetry_key, 33), 10)
        # Younger than the cutoff: untouched
        self.assertEqual(self.count(self.log_key, 2), 10)
        # Recompressed right after the DELETE
        self.assertEqual(self.partially_compressed_chunks(), 0)

    def test_deletes_from_uncompressed_chunks(self):
        self.add_day(33)

        self.assertEqual(purge_ts_kv_keys(), 10)
        self.assertEqual(self.count(self.log_key, 33), 0)
        self.assertEqual(self.count(self.telemetry_key, 33), 10)

    def test_nightly_run_skips_days_before_the_lookback(self):
        self.add_day(60)

        self.assertEqual(purge_ts_kv_keys(), 0)
        self.assertEqual(self.count(self.log_key, 60), 10)

        self.assertEqual(purge_ts_kv_keys(full=True), 10)
        self.assertEqual(self.count(self.log_key, 60), 0)

    @override_settings(TSKV_PURGE_KEYS=[])
    def test_empty_patterns_disable_the_purge(self):
        self.add_day(33)

        self.assertEqual(purge_ts_kv_keys(full=True), 0)
        self.assertEqual(self.count(self.log_key, 33), 10)
