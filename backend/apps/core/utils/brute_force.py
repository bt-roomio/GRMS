"""
Brute force protection key schema and unlock operations.

The single source of truth for how the Redis keys are shaped: the middleware
writes them, while the management command and the admin API read and delete
them. Keeping the format in one place is mandatory — otherwise unlocking
silently misses the keys the middleware actually sets.

The state of one (endpoint, email, ip) triple is just two keys:

* ``attempts``     — failure counter within the sliding ``attempt_window``;
* ``next_allowed`` — the instant until which attempts are rejected.

``next_allowed`` serves both the progressive delay and the full lockout: they
answer the same question, "when is it allowed again", so a separate ``lockout``
key is unnecessary. Extended windows are plain counters with the window TTL.
"""

import hashlib
import time
from collections.abc import Callable, Iterable
from typing import Any

from django.conf import settings
from django.core.cache import caches

security_cache = caches["security"]

KINDS = ("attempts", "next_allowed")


def hash_parts(*parts: str) -> str:
    """Hash for Redis keys — raw emails and IPs never reach Redis."""
    return hashlib.sha256(":".join(parts).encode()).hexdigest()[:16]


def normalize_email(email: str | None) -> str:
    """Normalized the same way as in the middleware, otherwise keys won't match."""
    if not isinstance(email, str):
        return "anonymous"
    return email.strip().lower() or "anonymous"


def key(kind: str, scope: str, email: str, ip: str) -> str:
    return f"bf:{kind}:{hash_parts(scope, email, ip)}"


def window_key(window_name: str, scope: str, email: str, ip: str) -> str:
    return f"bf:window:{window_name}:{hash_parts(scope, email, ip)}"


def ip_index_key(email: str) -> str:
    """Reverse index key: email -> IPs that produced failed attempts."""
    return f"bf:ips:{hash_parts(email)}"


def hard_block_key(ip: str) -> str:
    return f"bf:hard_block:{hash_parts(ip)}"


def incr_with_ttl(cache, cache_key: str, ttl: int, sliding: bool = False) -> int:
    """
    Atomically increment a counter, creating it when needed.

    ``add()`` goes first on purpose: starting with ``incr()`` and catching
    ``ValueError`` makes concurrent requests all fall into the creation branch
    when the key is missing, overwriting each other's increments. On a real
    Redis that lost up to 3/4 of the attempts and let the limit be bypassed
    with plain concurrency.

    ``sliding=True`` extends the TTL on every attempt (sliding counting window);
    extended windows have a fixed TTL that must never be extended.
    """
    if cache.add(cache_key, 1, ttl):
        return 1

    try:
        count = cache.incr(cache_key)
    except ValueError:
        # The key expired between add and incr — recreate it.
        cache.add(cache_key, 1, ttl)
        return 1

    if sliding:
        cache.touch(cache_key, ttl)
    return count


def _config() -> dict:
    return getattr(settings, "BRUTE_FORCE_CONFIG", {})


def _scopes() -> list[str]:
    return list(_config().get("protected_endpoints", []))


def _windows() -> dict:
    return _config().get("time_windows", {})


def index_ttl() -> int:
    """
    The index must outlive the longest possible lockout, otherwise there is
    nothing left to look up when unlocking.
    """
    config = _config()
    durations = [int(w.get("duration", 0)) for w in _windows().values()]
    return max([int(config.get("lockout_duration", 900)), *durations] or [900])


def remember_ip(email: str, ip: str, cache=None) -> None:
    """
    Remember the IP a failed attempt for this email came from.

    Without the index, unlocking by email alone is impossible: the lockout keys
    include the IP and an administrator does not know it. (django-axes does not
    support this operation in its cache backend at all — it raises
    NotImplementedError.)

    The read-modify-write is not atomic: a race may drop one IP from the index.
    That is not critical for unlocking — the admin sees the list and can pass
    the IP explicitly.
    """
    cache = cache or security_cache
    index = ip_index_key(email)
    known = cache.get(index, [])
    if ip in known:
        return
    known.append(ip)
    cache.set(index, known[-25:], index_ttl())


def known_ips(email: str, cache=None) -> list[str]:
    cache = cache or security_cache
    return list(cache.get(ip_index_key(email), []))


def _lock_checks(email: str, ip: str, now: float) -> list[tuple[str, Callable[[Any], dict | None]]]:
    """
    Every key that can lock ``email`` out from ``ip``, paired with a function
    turning the key's cached value into a lock description (or None).

    Keys are only listed here, not read, so a whole list of accounts can be
    checked with a single ``get_many``.
    """
    checks: list[tuple[str, Callable[[Any], dict | None]]] = [
        (
            hard_block_key(ip),
            lambda value: {"ip": ip, "endpoint": None, "reason": "hard_block", "seconds_left": None} if value else None,
        )
    ]

    for scope in _scopes():
        checks.append(
            (
                key("next_allowed", scope, email, ip),
                lambda value, scope=scope: (
                    {
                        "ip": ip,
                        "endpoint": scope,
                        "reason": "lockout",
                        "seconds_left": int(value - now),
                    }
                    if value and value > now
                    else None
                ),
            )
        )

        # An extended-window block stays active until the window counter
        # expires by TTL, so the exact time left is unknown.
        for window_name, window_config in _windows().items():
            checks.append(
                (
                    window_key(window_name, scope, email, ip),
                    lambda value, scope=scope, window_name=window_name, limit=window_config["max_attempts"]: (
                        {
                            "ip": ip,
                            "endpoint": scope,
                            "reason": f"window_{window_name}",
                            "seconds_left": None,
                        }
                        if (value or 0) >= limit
                        else None
                    ),
                )
            )

    return checks


def _collect_locks(email_ips: dict[str, list[str]], cache) -> dict[str, list[dict]]:
    """Active locks per email, read with one ``get_many`` for all emails and IPs."""
    now = time.time()
    checks = {
        email: [check for ip in ips for check in _lock_checks(email, ip, now)] for email, ips in email_ips.items()
    }
    values = cache.get_many({cache_key for email_checks in checks.values() for cache_key, _ in email_checks})
    return {
        email: [lock for cache_key, describe in email_checks if (lock := describe(values.get(cache_key)))]
        for email, email_checks in checks.items()
    }


def get_lock_status(email: str, cache=None) -> dict:
    """Returns whether the account is locked, from which IPs, and for how long."""
    cache = cache or security_cache
    email = normalize_email(email)
    ips = known_ips(email, cache)
    locks = _collect_locks({email: ips}, cache)[email]
    return {"email": email, "is_locked": bool(locks), "locks": locks, "known_ips": ips}


def locked_emails(emails: Iterable[str | None], cache=None) -> set[str]:
    """
    Normalized emails of the locked accounts among ``emails``.

    Batch counterpart of ``get_lock_status()["is_locked"]`` for user lists: two
    cache round trips in total instead of several per account.
    """
    cache = cache or security_cache
    index_keys = {ip_index_key(email): email for email in {normalize_email(e) for e in emails}}
    indexes = cache.get_many(list(index_keys))
    email_ips = {index_keys[index_key]: list(ips) for index_key, ips in indexes.items() if ips}
    return {email for email, locks in _collect_locks(email_ips, cache).items() if locks}


def unlock_account(email: str, ips: list[str] | None = None, cache=None) -> dict:
    """
    Lift a lockout caused by wrong passwords.

    Clears attempt counters, the lockout deadline and the extended windows
    across every protected endpoint. A permanent IP ban (hard_block) is NOT
    touched: it is set manually and lifted separately, otherwise unlocking an
    account would silently unban a malicious address.
    """
    cache = cache or security_cache
    email = normalize_email(email)
    targets = ips if ips is not None else known_ips(email, cache)

    keys = []
    for ip in targets:
        for scope in _scopes():
            keys.extend(key(kind, scope, email, ip) for kind in KINDS)
            keys.extend(window_key(name, scope, email, ip) for name in _windows())

    if keys:
        cache.delete_many(keys)
    cache.delete(ip_index_key(email))

    return {"email": email, "cleared_ips": list(targets), "cleared_keys": len(keys)}
