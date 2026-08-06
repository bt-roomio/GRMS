from channels.db import DatabaseSyncToAsync


def db(func):
    """
    Run ORM work from fleet's async code on a plain worker thread.

    Not channels' `database_sync_to_async`: that one is thread-sensitive, and
    these helpers also run underneath `ssh.run_blocking`, where the calling
    thread is already occupying asgiref's thread-sensitive executor and is
    blocked waiting on us. Submitting back onto it either deadlocks or raises
    "You cannot submit onto CurrentThreadExecutor from its own thread".

    Each of these calls is one self-contained write — pinning a host key,
    appending an audit row — so it has no reason to need the caller's thread.
    `DatabaseSyncToAsync` still closes stale connections around the call, so the
    worker thread does not leak one.
    """
    return DatabaseSyncToAsync(func, thread_sensitive=False)
