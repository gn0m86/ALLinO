from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from ..core.secrets import get_secret_value
from .base import BaseConnector, ConnectorHealth, RetryPolicy


def map_zoom_event_to_unified_event(
    event: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    event_id = str(event.get("id") or event.get("uuid") or "")
    if not event_id:
        raise ValueError("Zoom event id is required")

    start_time_raw = event.get("start_time")
    if isinstance(start_time_raw, str) and start_time_raw:
        timestamp = datetime.fromisoformat(start_time_raw.replace("Z", "+00:00"))
    else:
        timestamp = datetime.now(timezone.utc)

    topic = str(event.get("topic") or "")
    host = str(event.get("host_email") or event.get("host_id") or "")
    join_url = str(event.get("join_url") or "")

    preview_parts = [part for part in [topic, host] if part]
    preview = " | ".join(preview_parts) if preview_parts else event_id

    return {
        "eventId": f"zoom-meeting-{event_id}",
        "tenantId": tenant_id,
        "sourceType": "zoom",
        "externalId": event_id,
        "timestamp": timestamp.isoformat(),
        "payload": {
            "text": preview,
            "identifier": event_id,
            "topic": topic,
            "host": host,
            "url": join_url,
            "meeting_id": str(event.get("id") or ""),
            "meeting_uuid": str(event.get("uuid") or ""),
        },
        "schemaVersion": "1.0.0",
    }


class ZoomConnector(BaseConnector):
    def __init__(
        self,
        tenant_id: str,
        token: str | None = None,
        retry_policy: RetryPolicy | None = None,
        seeded_events: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(source="zoom", retry_policy=retry_policy)
        self.tenant_id = tenant_id
        self.token = token or get_secret_value("ALLINO_ZOOM_TOKEN")
        self._started = False
        self._seeded_events = seeded_events or []

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health(self) -> ConnectorHealth:
        if not self._started:
            status = "stopped"
        elif self.token or self._seeded_events:
            status = "healthy"
        else:
            status = "degraded"

        return ConnectorHealth(
            status=status,
            source=self.source,
            details={
                "has_token": bool(self.token),
                "seeded_events": len(self._seeded_events),
                "retry_count": self.last_retry_count,
            },
        )

    def fetch_events(self, cursor: str | None = None) -> Iterable[dict[str, Any]]:
        if not self._started:
            return []

        events = self._seeded_events
        if not events and self.token:
            events = self.run_with_retry(self._fetch_meetings_from_api)

        start_idx = int(cursor) if cursor else 0
        sliced = events[start_idx:]
        return [
            map_zoom_event_to_unified_event(item, tenant_id=self.tenant_id)
            for item in sliced
        ]

    def _fetch_meetings_from_api(self) -> list[dict[str, Any]]:
        if not self.token:
            return []

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://api.zoom.us/v2/users/me/meetings",
                params={"type": "scheduled", "page_size": 50},
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.token}",
                    "User-Agent": "allino-backend",
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            if not isinstance(payload, dict):
                return []
            meetings = payload.get("meetings") or []
            if not isinstance(meetings, list):
                return []
            return [item for item in meetings if isinstance(item, dict)]
