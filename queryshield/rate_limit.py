"""Per-IP token-bucket rate limiter.

In-process only — fine for the single-replica deploy we have today.
When we scale horizontally, swap the dict for Redis (`SETEX qs:rl:<ip>`).

Public surface: ``check(ip, key, limit, window_sec)`` returns
``(allowed, retry_after_sec)``.

Buckets are keyed by ``key`` so different routes can have different caps:
- /signup: 5 per 10 minutes per IP (anti-tenant-spam)
- /v1/query: 60 per minute per IP (defense-in-depth on top of tenant quota)
- /login: 10 per 10 minutes per IP
"""
from __future__ import annotations

import threading
import time
from typing import Tuple

_LOCK = threading.Lock()
# (ip, key) -> [hits-within-window]
_BUCKETS: dict[tuple[str, str], list[float]] = {}


def check(ip: str, key: str, limit: int, window_sec: int) -> Tuple[bool, int]:
    """Returns (allowed, retry_after_sec_if_blocked)."""
    now = time.time()
    cutoff = now - window_sec
    bucket_key = (ip, key)
    with _LOCK:
        bucket = _BUCKETS.get(bucket_key, [])
        # Drop entries outside the window.
        bucket = [t for t in bucket if t > cutoff]
        if len(bucket) >= limit:
            retry = max(1, int(bucket[0] + window_sec - now))
            _BUCKETS[bucket_key] = bucket
            return False, retry
        bucket.append(now)
        _BUCKETS[bucket_key] = bucket
    return True, 0


def client_ip(request) -> str:  # type: ignore[no-untyped-def]
    """Extract the client IP, trusting Railway's X-Forwarded-For when present."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"
