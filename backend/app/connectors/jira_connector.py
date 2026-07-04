from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from ..core.secrets import get_secret_value
from .base import BaseConnector, ConnectorHealth, RetryPolicy


def map_jira_issue_to_unified_event(
    issue: dict[str, Any],
    tenant_id: str,
    base_url: str | None = None,
) -> dict[str, Any]:
    external_id = str(issue.get("id") or "")
    identifier = str(issue.get("key") or "")
    if not external_id or not identifier:
        raise ValueError("Jira issue id and key are required")

    fields = issue.get("fields") or {}

    updated_at_raw = fields.get("updated")
    if isinstance(updated_at_raw, str):
        timestamp = datetime.fromisoformat(updated_at_raw.replace("Z", "+00:00"))
    else:
        timestamp = datetime.now(timezone.utc)

    summary = str(fields.get("summary") or "")
    project = fields.get("project") or {}
    project_key = str(project.get("key") or "")
    issue_type = fields.get("issuetype") or {}
    issue_type_name = str(issue_type.get("name") or "")

    preview_parts = [part for part in [project_key, identifier, summary, issue_type_name] if part]
    preview = " | ".join(preview_parts)

    issue_url = ""
    if base_url and identifier:
        issue_url = f"{base_url.rstrip('/')}/browse/{identifier}"

    return {
        "eventId": f"jira-issue-{external_id}",
        "tenantId": tenant_id,
        "sourceType": "jira",
        "externalId": external_id,
        "timestamp": timestamp.isoformat(),
        "payload": {
            "text": preview,
            "identifier": identifier,
            "url": issue_url,
            "project": project_key,
            "issue_type": issue_type_name,
        },
        "schemaVersion": "1.0.0",
    }


def send_jira_reply(
    *, token: str, external_id: str, text: str, base_url: str | None = None
) -> dict[str, Any]:
    if not external_id:
        raise ValueError("Jira reply requires external_id (the issue id)")

    resolved_base_url = (base_url or os.getenv("ALLINO_JIRA_BASE_URL") or "https://example.atlassian.net").rstrip("/")
    body = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
        }
    }

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"{resolved_base_url}/rest/api/3/issue/{external_id}/comment",
            json=body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "allino-backend",
            },
        )
        resp.raise_for_status()
        return resp.json()


class JiraConnector(BaseConnector):
    def __init__(
        self,
        tenant_id: str,
        token: str | None = None,
        base_url: str | None = None,
        retry_policy: RetryPolicy | None = None,
        seeded_issues: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(source="jira", retry_policy=retry_policy)
        self.tenant_id = tenant_id
        self.token = token or get_secret_value("ALLINO_JIRA_TOKEN")
        self.base_url = (base_url or os.getenv("ALLINO_JIRA_BASE_URL") or "https://example.atlassian.net").rstrip("/")
        self._started = False
        self._seeded_issues = seeded_issues or []

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health(self) -> ConnectorHealth:
        if not self._started:
            status = "stopped"
        elif self.token or self._seeded_issues:
            status = "healthy"
        else:
            status = "degraded"

        return ConnectorHealth(
            status=status,
            source=self.source,
            details={
                "has_token": bool(self.token),
                "base_url": self.base_url,
                "seeded_issues": len(self._seeded_issues),
                "retry_count": self.last_retry_count,
            },
        )

    def fetch_events(self, cursor: str | None = None) -> Iterable[dict[str, Any]]:
        if not self._started:
            return []

        issues = self._seeded_issues
        if not issues and self.token:
            issues = self.run_with_retry(self._fetch_issues_from_api)

        start_idx = int(cursor) if cursor else 0
        sliced = issues[start_idx:]
        return [
            map_jira_issue_to_unified_event(item, tenant_id=self.tenant_id, base_url=self.base_url)
            for item in sliced
        ]

    def _fetch_issues_from_api(self) -> list[dict[str, Any]]:
        if not self.token:
            return []

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{self.base_url}/rest/api/3/search",
                params={"jql": "ORDER BY updated DESC", "maxResults": 25},
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
            issues = payload.get("issues") or []
            if not isinstance(issues, list):
                return []
            return [item for item in issues if isinstance(item, dict)]
