from __future__ import annotations

from typing import Any, Iterable

from .base import BaseConnector, ConnectorHealth, RetryPolicy


class MockConnector(BaseConnector):
	def __init__(
		self,
		source: str = "mock",
		retry_policy: RetryPolicy | None = None,
		events: list[dict[str, Any]] | None = None,
	) -> None:
		super().__init__(source=source, retry_policy=retry_policy)
		self._started = False
		self._events = events or []

	def start(self) -> None:
		self._started = True

	def stop(self) -> None:
		self._started = False

	def health(self) -> ConnectorHealth:
		status = "healthy" if self._started else "stopped"
		return ConnectorHealth(
			status=status,
			source=self.source,
			details={
				"queued_events": len(self._events),
			},
		)

	def fetch_events(self, cursor: str | None = None) -> Iterable[dict[str, Any]]:
		if not self._started:
			return []

		start_idx = int(cursor) if cursor else 0
		return self._events[start_idx:]

	def seed_events(self, events: list[dict[str, Any]]) -> None:
		self._events.extend(events)
