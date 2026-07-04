from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from ..core.secrets import get_secret_value
from .base import BaseConnector, ConnectorHealth, RetryPolicy


def map_teams_message_to_unified_event(
    message: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    message_id = str(message.get("id") or "")
    if not message_id:
        raise ValueError("Teams message id is required")

    created_at_raw = message.get("createdDateTime")
    if isinstance(created_at_raw, str) and created_at_raw:
        timestamp = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
    else:
        timestamp = datetime.now(timezone.utc)

    body = message.get("body") or {}
    content = str(body.get("content") or message.get("summary") or "")
    sender_info = ((message.get("from") or {}).get("user") or {})
    sender = str(sender_info.get("displayName") or sender_info.get("id") or "")
    chat_id = str(message.get("chatId") or message.get("conversationId") or "")
    web_url = str(message.get("webUrl") or "")

    external_id = f"{chat_id}:{message_id}" if chat_id else message_id
    preview_parts = [part for part in [chat_id, sender, content] if part]
    preview = " | ".join(preview_parts) if preview_parts else external_id

    return {
        "eventId": f"teams-message-{external_id}",
        "tenantId": tenant_id,
        "sourceType": "teams",
        "externalId": external_id,
        "timestamp": timestamp.isoformat(),
        "payload": {
            "text": preview,
            # Stable per-chat anchor for thread grouping -- NOT external_id
            # (unique per message). Also deliberately NOT keyed "url": Teams'
            # webUrl is a permalink to this one specific message, not the chat,
            # so it must not be the thing _compute_thread_key anchors on either
            # (that field name is checked before "identifier"). See Sprint 31 board.
            "identifier": chat_id,
            "chat_id": chat_id,
            "sender": sender,
            "message_id": message_id,
            "message_url": web_url,
        },
        "schemaVersion": "1.0.0",
    }


class TeamsConnector(BaseConnector):
    def __init__(
        self,
        tenant_id: str,
        token: str | None = None,
        retry_policy: RetryPolicy | None = None,
        seeded_messages: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(source="teams", retry_policy=retry_policy)
        self.tenant_id = tenant_id
        self.token = token or get_secret_value("ALLINO_TEAMS_TOKEN")
        self._started = False
        self._seeded_messages = seeded_messages or []

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health(self) -> ConnectorHealth:
        if not self._started:
            status = "stopped"
        elif self.token or self._seeded_messages:
            status = "healthy"
        else:
            status = "degraded"

        return ConnectorHealth(
            status=status,
            source=self.source,
            details={
                "has_token": bool(self.token),
                "seeded_messages": len(self._seeded_messages),
                "retry_count": self.last_retry_count,
            },
        )

    def fetch_events(self, cursor: str | None = None) -> Iterable[dict[str, Any]]:
        if not self._started:
            return []

        messages = self._seeded_messages
        if not messages and self.token:
            messages = self.run_with_retry(self._fetch_messages_from_api)

        start_idx = int(cursor) if cursor else 0
        sliced = messages[start_idx:]
        return [
            map_teams_message_to_unified_event(item, tenant_id=self.tenant_id)
            for item in sliced
        ]

    def _fetch_messages_from_api(self) -> list[dict[str, Any]]:
        if not self.token:
            return []

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://graph.microsoft.com/v1.0/me/chats",
                params={"$top": 50},
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
            chats = payload.get("value") or []
            if not isinstance(chats, list):
                return []
            return [item for item in chats if isinstance(item, dict)]
