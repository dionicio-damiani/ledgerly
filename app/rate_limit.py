"""Lightweight in-memory rate limiter (sliding window).

Suitable for single-process deployments. For multi-process / multi-host
production, swap for a Redis-backed implementation.
"""

from __future__ import annotations

import asyncio
import re
from collections import deque
from time import monotonic
from typing import Final

from fastapi import HTTPException, Request, status

_UNIT_SECONDS: Final[dict[str, int]] = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
}


def parse_limit(spec: str) -> tuple[int, int]:
    """Parse strings like '30/minute' or '5/second' into (limit, window_seconds)."""
    match = re.fullmatch(r"\s*(\d+)\s*/\s*(second|minute|hour|day)\s*", spec)
    if not match:
        raise ValueError(f"Invalid rate-limit spec: {spec!r}")
    return int(match.group(1)), _UNIT_SECONDS[match.group(2)]


class InMemoryRateLimiter:
    """Per-key sliding window counter with bounded memory."""

    __slots__ = ("_buckets", "_lock", "_max_keys", "limit", "window")

    def __init__(self, spec: str, max_keys: int = 10_000) -> None:
        self.limit, self.window = parse_limit(spec)
        self._buckets: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()
        self._max_keys = max_keys

    async def hit(self, key: str) -> bool:
        """Record a hit for `key`. Returns True if allowed, False if over the limit."""
        now = monotonic()
        cutoff = now - self.window
        async with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                if len(self._buckets) >= self._max_keys:
                    self._evict_stale(cutoff)
                bucket = deque()
                self._buckets[key] = bucket

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.limit:
                return False

            bucket.append(now)
            return True

    def _evict_stale(self, cutoff: float) -> None:
        for k in [k for k, b in self._buckets.items() if not b or b[-1] <= cutoff]:
            self._buckets.pop(k, None)

    def reset(self) -> None:
        self._buckets.clear()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_dependency(limiter: InMemoryRateLimiter, scope: str = "default"):
    """Build a FastAPI dependency that enforces `limiter` for a given `scope`."""

    async def _dependency(request: Request) -> None:
        key = f"{scope}:{client_ip(request)}"
        if not await limiter.hit(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({limiter.limit}/{limiter.window}s)",
            )

    return _dependency
