from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from ..core.secrets import get_secret_value
from .base import BaseConnector, ConnectorHealth, RetryPolicy


def map_linear_event_to_unified_event(
    event_payload: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    external_id = str(event_payload.get("id") or "")
    if not external_id:
        raise ValueError("Linear event id is required")

    created_at_raw = event_payload.get("createdAt") or event_payload.get("updatedAt")
    if isinstance(created_at_raw, str):
        timestamp = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
    else:
        timestamp = datetime.now(timezone.utc)

    title = str(event_payload.get("title") or "")
    team = event_payload.get("team") or {}
    team_key = str(team.get("key") or "")
    state = event_payload.get("state") or {}
    state_name = str(state.get("name") or "")

    preview_parts = [part for part in [team_key, title, state_name] if part]
    preview = " | ".join(preview_parts)

    return {
        "eventId": f"linear-issue-{external_id}",
        "tenantId": tenant_id,
        "sourceType": "linear",
        "externalId": external_id,
        "timestamp": timestamp.isoformat(),
        "payload": {
            "text": preview,
            "identifier": str(event_payload.get("identifier") or ""),
            "url": str(event_payload.get("url") or ""),
            "team": team_key,
            "state": state_name,
        },
        "schemaVersion": "1.0.0",
    }


def send_linear_reply(*, token: str, external_id: str, text: str) -> dict[str, Any]:
    if not external_id:
        raise ValueError("Linear reply requires external_id (the issue id)")

    gql = (
        "mutation($issueId: String!, $body: String!) { "
        "commentCreate(input: {issueId: $issueId, body: $body}) { success } }"
    )

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            "https://api.linear.app/graphql",
            json={"query": gql, "variables": {"issueId": external_id, "body": text}},
            headers={
                "Accept": "application/json",
                "Authorization": token,
                "User-Agent": "allino-backend",
            },
        )
        resp.raise_for_status()
        payload = resp.json()

    if isinstance(payload, dict) and payload.get("errors"):
        raise RuntimeError(f"Linear API error: {payload['errors']}")
    success = bool((payload.get("data") or {}).get("commentCreate", {}).get("success"))
    if not success:
        raise RuntimeError("Linear API error: commentCreate did not succeed")
    return payload


class LinearConnector(BaseConnector):
    def __init__(
        self,
        tenant_id: str,
        token: str | None = None,
        retry_policy: RetryPolicy | None = None,
        seeded_events: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(source="linear", retry_policy=retry_policy)
        self.tenant_id = tenant_id
        self.token = token or get_secret_value("ALLINO_LINEAR_TOKEN")
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
            map_linear_event_to_unified_event(item, tenant_id=self.tenant_id)
            for item in sliced
        ]

    def _fetch_events_from_api(self) -> list[dict[str, Any]]:
        if not self.token:
            return []

        gql = "query { issues(first: 25) { nodes { id identifier title url createdAt updatedAt state { name } team { key } } } }"

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "https://api.linear.app/graphql",
                json={"query": gql},
                headers={
                    "Accept": "application/json",
                    "Authorization": self.token,
                    "User-Agent": "allino-backend",
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            if not isinstance(payload, dict):
                return []
            data = payload.get("data") or {}
            issues = data.get("issues") or {}
            nodes = issues.get("nodes") or []
            if not isinstance(nodes, list):
                return []
            return [item for item in nodes if isinstance(item, dict)]
