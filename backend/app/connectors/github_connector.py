from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from ..core.secrets import get_secret_value
from .base import BaseConnector, ConnectorHealth, RetryPolicy


def map_github_notification_to_unified_event(
    notification: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    subject = notification.get("subject") or {}
    repository = notification.get("repository") or {}

    external_id = str(notification.get("id") or "")
    if not external_id:
        raise ValueError("GitHub notification id is required")

    updated_at_raw = notification.get("updated_at")
    if isinstance(updated_at_raw, str):
        timestamp = datetime.fromisoformat(updated_at_raw.replace("Z", "+00:00"))
    else:
        timestamp = datetime.now(timezone.utc)

    title = str(subject.get("title") or "")
    repo_name = str(repository.get("full_name") or "")
    reason = str(notification.get("reason") or "")

    preview_parts = [part for part in [repo_name, title, reason] if part]
    preview = " | ".join(preview_parts)

    return {
        "eventId": f"gh-notification-{external_id}",
        "tenantId": tenant_id,
        "sourceType": "github",
        "externalId": external_id,
        "timestamp": timestamp.isoformat(),
        "payload": {
            "text": preview,
            "subject_type": str(subject.get("type") or ""),
            "subject_url": str(subject.get("url") or ""),
            "repository": repo_name,
            "reason": reason,
        },
        "schemaVersion": "1.0.0",
    }


def send_github_reply(
    *, token: str, external_id: str, text: str, reply_target: str | None = None
) -> dict[str, Any]:
    if not reply_target:
        raise ValueError("GitHub reply requires reply_target (the issue/PR API URL)")

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"{reply_target}/comments",
            json={"body": text},
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "allino-backend",
            },
        )
        resp.raise_for_status()
        return resp.json()


class GitHubConnector(BaseConnector):
    def __init__(
        self,
        tenant_id: str,
        token: str | None = None,
        retry_policy: RetryPolicy | None = None,
        seeded_notifications: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(source="github", retry_policy=retry_policy)
        self.tenant_id = tenant_id
        self.token = token or get_secret_value("ALLINO_GITHUB_TOKEN")
        self._started = False
        self._seeded_notifications = seeded_notifications or []

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health(self) -> ConnectorHealth:
        if not self._started:
            status = "stopped"
        elif self.token or self._seeded_notifications:
            status = "healthy"
        else:
            status = "degraded"

        return ConnectorHealth(
            status=status,
            source=self.source,
            details={
                "has_token": bool(self.token),
                "seeded_notifications": len(self._seeded_notifications),
                "retry_count": self.last_retry_count,
            },
        )

    def fetch_events(self, cursor: str | None = None) -> Iterable[dict[str, Any]]:
        if not self._started:
            return []

        notifications = self._seeded_notifications
        if not notifications and self.token:
            notifications = self.run_with_retry(self._fetch_notifications_from_api)

        start_idx = int(cursor) if cursor else 0
        sliced = notifications[start_idx:]
        return [
            map_github_notification_to_unified_event(item, tenant_id=self.tenant_id)
            for item in sliced
        ]

    def _fetch_notifications_from_api(self) -> list[dict[str, Any]]:
        if not self.token:
            return []

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://api.github.com/notifications",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {self.token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "allino-backend",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                return []
            return [item for item in data if isinstance(item, dict)]
