from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import sleep
from typing import Any, Callable, Iterable, Literal, TypeVar

import httpx


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 0.2


@dataclass(frozen=True)
class ConnectorHealth:
    status: Literal["starting", "healthy", "stopped", "degraded", "error"]
    source: str
    details: dict[str, Any]


T = TypeVar("T")


class BaseConnector(ABC):
    source: str

    def __init__(self, source: str, retry_policy: RetryPolicy | None = None) -> None:
        self.source = source
        self.retry_policy = retry_policy or RetryPolicy()
        self.last_retry_count = 0

    @abstractmethod
    def start(self) -> None:
        """Initialize connector resources and mark connector as running."""

    @abstractmethod
    def stop(self) -> None:
        """Gracefully stop connector and release any resources."""

    @abstractmethod
    def health(self) -> ConnectorHealth:
        """Return current connector health for readiness monitoring."""

    @abstractmethod
    def fetch_events(self, cursor: str | None = None) -> Iterable[dict[str, Any]]:
        """Fetch provider events and yield raw event dictionaries."""

    def run_with_retry(self, op: Callable[[], T]) -> T:
        last_error: Exception | None = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                result = op()
                self.last_retry_count = attempt - 1
                return result
            except Exception as exc:  # pragma: no cover - expected control path on failures
                last_error = exc
                if not self._is_retryable_exception(exc):
                    self.last_retry_count = attempt - 1
                    raise
                if attempt >= self.retry_policy.max_attempts:
                    break
                sleep(self.retry_policy.backoff_seconds)

        self.last_retry_count = self.retry_policy.max_attempts - 1
        if last_error is None:
            raise RuntimeError("Connector retry failed without explicit error")
        raise last_error

    def _is_retryable_exception(self, exc: Exception) -> bool:
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            if code == 429:
                return True
            if 400 <= code < 500:
                return False
            return True
        return True
