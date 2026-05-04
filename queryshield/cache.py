"""Result cache + schema cache.

Two-tier:
- Redis if REDIS_URL is set (shared between API replicas).
- Otherwise an in-process dict with TTL.

The cache is intentionally narrow: keyed by (tenant, alias, sql-hash). We
never cache rows when ``cached=False`` is requested in the QueryRequest
(future flag — keeps the engine flexible).
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from queryshield.config import get_settings

log = logging.getLogger("queryshield.cache")

_PROCESS_CACHE: dict[str, tuple[float, str]] = {}


def _redis_client():  # type: ignore[no-untyped-def]
    """Lazy single client; returns None if redis isn't configured / reachable."""
    url = get_settings().redis_url
    if not url:
        return None
    try:
        import redis  # type: ignore

        return redis.Redis.from_url(url, decode_responses=True, socket_timeout=2)
    except Exception as e:  # noqa: BLE001
        log.warning("cache: redis unavailable, falling back to in-process: %s", e)
        return None


_REDIS = None
_REDIS_INIT = False


def _redis():
    global _REDIS, _REDIS_INIT
    if not _REDIS_INIT:
        _REDIS = _redis_client()
        _REDIS_INIT = True
    return _REDIS


async def cache_get_json(key: str) -> Optional[Any]:
    r = _redis()
    if r is not None:
        try:
            value = r.get(key)
            if value is not None:
                return json.loads(value)
        except Exception as e:  # noqa: BLE001
            log.debug("cache: redis get failed: %s", e)

    entry = _PROCESS_CACHE.get(key)
    if entry and entry[0] > time.time():
        return json.loads(entry[1])
    if entry:
        _PROCESS_CACHE.pop(key, None)
    return None


async def cache_set_json(key: str, value: Any, ttl: int = 300) -> None:
    blob = json.dumps(value, default=str)
    r = _redis()
    if r is not None:
        try:
            r.set(key, blob, ex=ttl)
        except Exception as e:  # noqa: BLE001
            log.debug("cache: redis set failed: %s", e)
    _PROCESS_CACHE[key] = (time.time() + ttl, blob)


async def cache_delete(key: str) -> None:
    _PROCESS_CACHE.pop(key, None)
    r = _redis()
    if r is not None:
        try:
            r.delete(key)
        except Exception as e:  # noqa: BLE001
            log.debug("cache: redis del failed: %s", e)
