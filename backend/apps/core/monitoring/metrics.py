from django.db import connection
from prometheus_client import Gauge

# Important for gunicorn/uvicorn with multiple workers:
# sums values across processes
DB_CONN_GAUGE = Gauge(
    "django_db_connections",
    "PostgreSQL connections by state for current_database()",
    ["state"],  # active | idle | idle in transaction | unknown
    multiprocess_mode="max",
)

DB_CONN_TOTAL = Gauge(
    "django_db_connections_total",
    "Total PostgreSQL connections for current_database()",
    multiprocess_mode="max",
)

DB_MAX_CONN = Gauge(
    "django_db_max_connections",
    "PostgreSQL max_connections",
    multiprocess_mode="max",
)

# Optional: connections per user (handy for Grafana filters)
DB_CONN_BY_USER = Gauge(
    "django_db_connections_by_user",
    "PostgreSQL connections by user for current_database()",
    ["usename"],
    multiprocess_mode="max",
)


def refresh_db_connection_metrics() -> None:
    """
    Reads pg_stat_activity and pg_settings and sets the metrics.
    Safe to call from Celery beat/cron or a background thread.
    """
    # 1) max_connections
    with connection.cursor() as cur:
        cur.execute("SELECT setting::int FROM pg_settings WHERE name = 'max_connections'")
        (max_conn,) = cur.fetchone()
        DB_MAX_CONN.set(max_conn)

    # 2) by state
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(state, 'unknown') AS state, COUNT(*)::bigint
            FROM pg_stat_activity
            WHERE datname = current_database()
            GROUP BY COALESCE(state, 'unknown')
            """
        )
        rows = cur.fetchall()

    # First zero out the known labels,
    # so the metric doesn't "stick" when some state disappears.
    for st in ("active", "idle", "idle in transaction", "unknown"):
        DB_CONN_GAUGE.labels(state=st).set(0)

    total = 0
    for state, cnt in rows:
        DB_CONN_GAUGE.labels(state=state).set(cnt)
        total += cnt

    DB_CONN_TOTAL.set(total)

    # 3) by user
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT usename, COUNT(*)::bigint
            FROM pg_stat_activity
            WHERE datname = current_database()
            GROUP BY usename
            """
        )
        user_rows = cur.fetchall()

    # Existing values can't be reset without storing the list of labels,
    # so we just set the current ones; "old" ones disappear when the worker restarts.
    for usename, cnt in user_rows:
        DB_CONN_BY_USER.labels(usename=usename or "<none>").set(cnt)
