"""
Purge of selected shuttle_ts_kv keys (device logs, events, errors) older than
TSKV_PURGE_AFTER_DAYS, while the rest of the telemetry is kept.

Rows are deleted one chunk (one UTC day) at a time, and only from chunks that lie entirely
before the cutoff. The DELETE always goes through the hypertable: a DELETE on a chunk's own
table only sees its uncompressed part and silently skips the compressed data. With a filter
on ts TimescaleDB cannot drop compressed batches as a whole, so it decompresses the batches
of the purged keys and deletes the rows; the chunk is recompressed afterwards.
"""

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from fnmatch import fnmatchcase

from django.conf import settings
from django.db import OperationalError, connection, transaction
from django.utils import timezone
from psycopg2 import errorcodes as pg_errorcodes

from shuttle.models import TsKvDictionary

logger = logging.getLogger(__name__)

# A nightly run revisits only the chunks that crossed the cutoff lately, which also covers a
# few missed nights. A pass over the whole history is `manage.py purge_ts_kv_keys --all`.
NIGHTLY_LOOKBACK = timedelta(days=7)
FULL_HISTORY_START = datetime(1970, 1, 1, tzinfo=UTC)

CHUNKS_SQL = """
SELECT format('%%I.%%I', chunk_schema, chunk_name), range_start, range_end, is_compressed
FROM timescaledb_information.chunks
WHERE hypertable_schema = 'public' AND hypertable_name = 'shuttle_ts_kv'
  AND range_end <= %s AND range_end > %s
ORDER BY range_start
"""


@dataclass(frozen=True)
class Chunk:
    name: str
    range_start: datetime
    range_end: datetime
    is_compressed: bool


@dataclass(frozen=True)
class ChunkPurge:
    chunk: Chunk
    deleted: int = 0
    # The DELETE gave up on lock_timeout; the next run retries the chunk.
    skipped: bool = False


def match_purge_keys(patterns: list[str]) -> dict[int, str]:
    """Map key_id -> key for every dictionary key matching one of the glob patterns."""
    return {
        key_id: key
        for key_id, key in TsKvDictionary.objects.values_list("key_id", "key")
        if any(fnmatchcase(key, pattern) for pattern in patterns)
    }


def purge_cutoff() -> datetime:
    return timezone.now() - timedelta(days=settings.TSKV_PURGE_AFTER_DAYS)


def chunks_to_purge(*, full: bool = False) -> list[Chunk]:
    """Chunks entirely older than the cutoff: all of them, or only those of the last nights."""
    cutoff = purge_cutoff()
    since = FULL_HISTORY_START if full else cutoff - NIGHTLY_LOOKBACK
    with connection.cursor() as cursor:
        cursor.execute(CHUNKS_SQL, [cutoff, since])
        return [Chunk(*row) for row in cursor.fetchall()]


def _is_lock_timeout(exc: OperationalError) -> bool:
    return getattr(exc.__cause__, "pgcode", None) == pg_errorcodes.LOCK_NOT_AVAILABLE


def purge_chunk(chunk: Chunk, key_ids: list[int]) -> ChunkPurge:
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            # Fail fast instead of queueing behind pg_dump or compression (and blocking inserts).
            cursor.execute("SET LOCAL lock_timeout = '5s'")
            # The default cap of 100k decompressed tuples per transaction is below one day of logs.
            cursor.execute("SET LOCAL timescaledb.max_tuples_decompressed_per_dml_transaction = 0")
            cursor.execute(
                "DELETE FROM shuttle_ts_kv WHERE key = ANY(%s) AND ts >= %s AND ts < %s",
                [key_ids, chunk.range_start, chunk.range_end],
            )
            deleted = cursor.rowcount
    except OperationalError as exc:
        if not _is_lock_timeout(exc):
            raise
        logger.warning("ts_kv purge: %s is locked, skipped: %s", chunk.name, exc)
        return ChunkPurge(chunk, skipped=True)

    if deleted and chunk.is_compressed:
        # The DELETE leaves the chunk partially compressed. Recompress it now instead of
        # spending the compression policy's per-run chunk budget on it.
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout = '5s'")
                cursor.execute("SELECT compress_chunk(%s::regclass)", [chunk.name])
        except OperationalError as exc:
            if not _is_lock_timeout(exc):
                raise
            logger.warning("ts_kv purge: %s is locked, left to the compression policy: %s", chunk.name, exc)

    return ChunkPurge(chunk, deleted=deleted)


def purge_ts_kv_keys(*, full: bool = False, time_budget: float | None = None) -> int:
    """
    Delete rows of the TSKV_PURGE_KEYS keys older than TSKV_PURGE_AFTER_DAYS, oldest chunk
    first. Every chunk is committed on its own, so a run cut short by time_budget (seconds)
    loses nothing and the next run carries on. Returns the number of deleted rows.
    """
    patterns = settings.TSKV_PURGE_KEYS
    if not patterns:
        return 0
    keys = match_purge_keys(patterns)
    if not keys:
        logger.warning("ts_kv purge: no keys match %s", " ".join(patterns))
        return 0

    deadline = time.monotonic() + time_budget if time_budget is not None else None
    chunks = chunks_to_purge(full=full)
    total = skipped = done = 0
    for chunk in chunks:
        if deadline is not None and time.monotonic() >= deadline:
            logger.warning("ts_kv purge: time budget spent, %s chunk(s) left for the next run", len(chunks) - done)
            break
        result = purge_chunk(chunk, list(keys))
        total += result.deleted
        skipped += result.skipped
        done += 1

    logger.info(
        "ts_kv purge: %s row(s) deleted in %s chunk(s), %s skipped; keys: %s",
        total,
        done,
        skipped,
        ", ".join(sorted(keys.values())),
    )
    return total
