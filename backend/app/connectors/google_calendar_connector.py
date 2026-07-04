from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import httpx

from ..core.secrets import get_secret_value
from .base import BaseConnector, ConnectorHealth, RetryPolicy


def map_google_calendar_event_to_unified_event(
    event: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    event_id = str(event.get("id") or "")
    if not event_id:
        raise ValueError("Google Calendar event id is required")

    start = event.get("start") or {}
    start_raw = start.get("dateTime") or start.get("date")
    if isinstance(start_raw, str) and start_raw:
        try:
            timestamp = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
        except ValueError:
            timestamp = datetime.now(timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)

    summary = str(event.get("summary") or "")
    organizer = str((event.get("organizer") or {}).get("email") or "")
    status = str(event.get("status") or "")
    html_link = str(event.get("htmlLink") or "")

    meet_url = ""
    conference_data = event.get("conferenceData") or {}
    for entry_point in conference_data.get("entryPoints") or []:
        if isinstance(entry_point, dict) and entry_point.get("entryPointType") == "video":
            meet_url = str(entry_point.get("uri") or "")
            break
    if not meet_url:
        meet_url = str(event.get("hangoutLink") or "")

    preview_parts = [part for part in [summary, organizer] if part]
    preview = " | ".join(preview_parts) if preview_parts else event_id
    if status == "cancelled":
        preview = f"[Cancelled] {preview}"

    return {
        "eventId": f"google-calendar-event-{event_id}",
        "tenantId": tenant_id,
        "sourceType": "google_calendar",
        "externalId": event_id,
        "timestamp": timestamp.isoformat(),
        "payload": {
            "text": preview,
            "identifier": event_id,
            "summary": summary,
            "organizer": organizer,
            "status": status,
            "url": html_link,
            "meet_url": meet_url,
        },
        "schemaVersion": "1.0.0",
    }


class GoogleCalendarConnector(BaseConnector):
    def __init__(
        self,
        tenant_id: str,
        token: str | None = None,
        calendar_id: str | None = None,
        retry_policy: RetryPolicy | None = None,
        seeded_events: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(source="google_calendar", retry_policy=retry_policy)
        self.tenant_id = tenant_id
        self.token = token or get_secret_value("ALLINO_GOOGLE_CALENDAR_TOKEN")
        self.calendar_id = calendar_id or "primary"
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
            events = self.run_with_retry(self._fetch_events_from_api)

        start_idx = int(cursor) if cursor else 0
        sliced = events[start_idx:]
        return [
            map_google_calendar_event_to_unified_event(item, tenant_id=self.tenant_id)
            for item in sliced
        ]

    def _fetch_events_from_api(self) -> list[dict[str, Any]]:
        if not self.token:
            return []

        time_min = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events",
                params={
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 50,
                    "timeMin": time_min,
                },
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
            items = payload.get("items") or []
            if not isinstance(items, list):
                return []
            return [item for item in items if isinstance(item, dict)]
