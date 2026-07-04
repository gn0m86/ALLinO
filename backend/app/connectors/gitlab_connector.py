from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import quote, urlparse

import httpx

from ..core.secrets import get_secret_value
from .base import BaseConnector, ConnectorHealth, RetryPolicy

_NOTEABLE_TYPES = {"issues", "merge_requests"}


def map_gitlab_notification_to_unified_event(
    notification: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    event_id_raw = notification.get("id")
    external_id = str(event_id_raw or "")
    if not external_id:
        raise ValueError("GitLab notification id is required")

    created_at_raw = notification.get("created_at") or notification.get("updated_at")
    if isinstance(created_at_raw, str):
        timestamp = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
    else:
        timestamp = datetime.now(timezone.utc)

    project = notification.get("project") or {}
    project_name = str(project.get("path_with_namespace") or project.get("name") or "")
    target_title = str(notification.get("target_title") or "")
    action_name = str(notification.get("action_name") or "")

    preview_parts = [part for part in [project_name, target_title, action_name] if part]
    preview = " | ".join(preview_parts)

    return {
        "eventId": f"gl-notification-{external_id}",
        "tenantId": tenant_id,
        "sourceType": "gitlab",
        "externalId": external_id,
        "timestamp": timestamp.isoformat(),
        "payload": {
            "text": preview,
            "target_type": str(notification.get("target_type") or ""),
            "target_url": str(notification.get("target_url") or ""),
            "project": project_name,
            "action_name": action_name,
        },
        "schemaVersion": "1.0.0",
    }


def _parse_gitlab_target(target_url: str) -> tuple[str, str, str]:
    path = urlparse(target_url).path.strip("/")
    parts = path.split("/-/")
    if len(parts) != 2:
        raise ValueError(f"Unrecognized GitLab target_url shape: {target_url!r}")

    project_path = parts[0]
    rest = parts[1].split("/")
    if len(rest) < 2:
        raise ValueError(f"Unrecognized GitLab target_url shape: {target_url!r}")

    noteable_type = rest[0]
    iid = rest[1].split("#")[0]
    if noteable_type not in _NOTEABLE_TYPES or not project_path or not iid:
        raise ValueError(f"Unrecognized GitLab target_url shape: {target_url!r}")

    return project_path, noteable_type, iid


def send_gitlab_reply(
    *,
    token: str,
    external_id: str,
    text: str,
    reply_target: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    if not reply_target:
        raise ValueError("GitLab reply requires reply_target (the issue/MR web URL)")

    project_path, noteable_type, iid = _parse_gitlab_target(reply_target)
    resolved_base_url = (base_url or os.getenv("ALLINO_GITLAB_BASE_URL") or "https://gitlab.com").rstrip("/")
    encoded_project = quote(project_path, safe="")

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"{resolved_base_url}/api/v4/projects/{encoded_project}/{noteable_type}/{iid}/notes",
            json={"body": text},
            headers={
                "Accept": "application/json",
                "PRIVATE-TOKEN": token,
                "User-Agent": "allino-backend",
            },
        )
        resp.raise_for_status()
        return resp.json()


class GitLabConnector(BaseConnector):
    def __init__(
        self,
        tenant_id: str,
        token: str | None = None,
        base_url: str | None = None,
        retry_policy: RetryPolicy | None = None,
        seeded_notifications: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(source="gitlab", retry_policy=retry_policy)
        self.tenant_id = tenant_id
        self.token = token or get_secret_value("ALLINO_GITLAB_TOKEN")
        self.base_url = (base_url or os.getenv("ALLINO_GITLAB_BASE_URL") or "https://gitlab.com").rstrip("/")
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
                "base_url": self.base_url,
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
            map_gitlab_notification_to_unified_event(item, tenant_id=self.tenant_id)
            for item in sliced
        ]

    def _fetch_notifications_from_api(self) -> list[dict[str, Any]]:
        if not self.token:
            return []

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{self.base_url}/api/v4/notifications",
                params={"per_page": 50},
                headers={
                    "Accept": "application/json",
                    "PRIVATE-TOKEN": self.token,
                    "User-Agent": "allino-backend",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                return []
            return [item for item in data if isinstance(item, dict)]
