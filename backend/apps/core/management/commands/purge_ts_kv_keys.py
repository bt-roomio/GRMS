from django.conf import settings
from django.core.management.base import BaseCommand

from shuttle.services.ts_kv_purge import chunks_to_purge, match_purge_keys, purge_chunk, purge_cutoff


class Command(BaseCommand):
    help = (
        "Delete rows of the TSKV_PURGE_KEYS keys older than TSKV_PURGE_AFTER_DAYS from shuttle_ts_kv. "
        "The nightly task only revisits the last days; use --all after the first rollout "
        "or after adding a pattern."
    )

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Go through the whole history, not just the last days.")
        parser.add_argument("--dry-run", action="store_true", help="Show the matched keys and chunks, delete nothing.")

    def handle(self, *args, **options):
        patterns = settings.TSKV_PURGE_KEYS
        if not patterns:
            self.stdout.write("TSKV_PURGE_KEYS is empty, nothing to purge.")
            return

        keys = match_purge_keys(patterns)
        self.stdout.write(f"Patterns: {' '.join(patterns)}")
        self.stdout.write(f"Matched keys ({len(keys)}): {', '.join(sorted(keys.values())) or '-'}")
        if not keys:
            return

        chunks = chunks_to_purge(full=options["all"])
        self.stdout.write(
            f"Cutoff: {purge_cutoff():%Y-%m-%d %H:%M %Z} ({settings.TSKV_PURGE_AFTER_DAYS} days), "
            f"chunks to process: {len(chunks)}"
        )
        if options["dry_run"]:
            for chunk in chunks:
                state = "compressed" if chunk.is_compressed else "uncompressed"
                self.stdout.write(f"  {chunk.range_start:%Y-%m-%d}  {chunk.name}  {state}")
            return

        total = skipped = 0
        for chunk in chunks:
            result = purge_chunk(chunk, list(keys))
            total += result.deleted
            skipped += result.skipped
            status = "SKIPPED (locked)" if result.skipped else f"{result.deleted} row(s)"
            self.stdout.write(f"  {chunk.range_start:%Y-%m-%d}  {chunk.name}  {status}")

        self.stdout.write(self.style.SUCCESS(f"Deleted {total} row(s); skipped {skipped} chunk(s)."))
