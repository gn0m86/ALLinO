from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import time
from typing import Deque

from fastapi import Request

# Re-exported as module attributes: main.py reads them via `rate_limit.X` (not a
# direct `from .config import X`) so tests can monkeypatch this module in one place.
from .config import (
    ALLINO_RATE_LIMIT_ENABLED,  # noqa: F401
    ALLINO_RATE_LIMIT_REQUESTS,  # noqa: F401
    ALLINO_RATE_LIMIT_WINDOW_SECONDS,  # noqa: F401
)


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def consume(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time()
        with self._lock:
            bucket = self._events[key]
            threshold = now - window_seconds
            while bucket and bucket[0] <= threshold:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                return False, retry_after

            bucket.append(now)
            return True, 0


def is_rate_limited_path(path: str) -> bool:
    return (
        path.startswith("/api/v1/ingestion")
        or path.startswith("/webhooks")
        or path.startswith("/api/v1/admin")
    )


def rate_limit_key(request: Request) -> str:
    client_ip = request.client.host if request.client else "unknown"
    tenant = request.headers.get("X-Tenant-Id") or request.query_params.get("tenant_id") or "_"
    return f"{client_ip}:{tenant}"


RATE_LIMITER = InMemoryRateLimiter()
