from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from ..core.secrets import get_secret_value
from .base import BaseConnector, ConnectorHealth, RetryPolicy


def map_discord_message_to_unified_event(
    message: dict[str, Any],
    *,
    tenant_id: str,
    channel_id: str | None = None,
) -> dict[str, Any]:
    message_id = str(message.get("id") or "")
    if not message_id:
        raise ValueError("Discord message id is required")

    created_at_raw = message.get("timestamp")
    if isinstance(created_at_raw, str):
        timestamp = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
    else:
        timestamp = datetime.now(timezone.utc)

    content = str(message.get("content") or "")
    author = message.get("author") or {}
    sender = str(author.get("username") or author.get("id") or "")
    channel = channel_id or str(message.get("channel_id") or "")

    external_id = f"{channel}:{message_id}" if channel else message_id
    preview_parts = [part for part in [channel, sender, content] if part]
    preview = " | ".join(preview_parts)

    return {
        "eventId": f"discord-message-{external_id}",
        "tenantId": tenant_id,
        "sourceType": "discord",
        "externalId": external_id,
        "timestamp": timestamp.isoformat(),
        "payload": {
            "text": preview,
            # Stable per-channel anchor for thread grouping -- NOT external_id,
            # which is unique per message and would put every message in its
            # own "thread". See Sprint 31 board.
            "identifier": channel,
            "channel": channel,
            "sender": sender,
            "message_id": message_id,
        },
        "schemaVersion": "1.0.0",
    }


def send_discord_reply(*, token: str, external_id: str, text: str) -> dict[str, Any]:
    channel, _, message_id = external_id.partition(":")
    if not channel:
        raise ValueError("Discord external_id must be in 'channel:message_id' format")

    body: dict[str, Any] = {"content": text}
    if message_id:
        body["message_reference"] = {"message_id": message_id}

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"https://discord.com/api/v10/channels/{channel}/messages",
            json=body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bot {token}",
                "User-Agent": "allino-backend",
            },
        )
        resp.raise_for_status()
        return resp.json()


class DiscordConnector(BaseConnector):
    def __init__(
        self,
        tenant_id: str,
        token: str | None = None,
        channel_id: str | None = None,
        retry_policy: RetryPolicy | None = None,
        seeded_messages: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(source="discord", retry_policy=retry_policy)
        self.tenant_id = tenant_id
        self.token = token or get_secret_value("ALLINO_DISCORD_BOT_TOKEN")
        self.channel_id = channel_id or get_secret_value("ALLINO_DISCORD_CHANNEL_ID")
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
                "channel_id": self.channel_id,
                "seeded_messages": len(self._seeded_messages),
                "retry_count": self.last_retry_count,
            },
        )

    def fetch_events(self, cursor: str | None = None) -> Iterable[dict[str, Any]]:
        if not self._started:
            return []

        messages = self._seeded_messages
        if not messages and self.token and self.channel_id:
            messages = self.run_with_retry(self._fetch_messages_from_api)

        start_idx = int(cursor) if cursor else 0
        sliced = messages[start_idx:]
        return [
            map_discord_message_to_unified_event(item, tenant_id=self.tenant_id, channel_id=self.channel_id)
            for item in sliced
        ]

    def _fetch_messages_from_api(self) -> list[dict[str, Any]]:
        if not self.token or not self.channel_id:
            return []

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"https://discord.com/api/v10/channels/{self.channel_id}/messages",
                params={"limit": 50},
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bot {self.token}",
                    "User-Agent": "allino-backend",
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            if not isinstance(payload, list):
                return []
            return [item for item in payload if isinstance(item, dict)]
