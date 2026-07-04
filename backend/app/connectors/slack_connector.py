from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from ..core.secrets import get_secret_value
from .base import BaseConnector, ConnectorHealth, RetryPolicy


def map_slack_message_to_unified_event(
    message: dict[str, Any],
    *,
    tenant_id: str,
    channel_id: str | None = None,
) -> dict[str, Any]:
    ts_raw = str(message.get("ts") or "")
    if not ts_raw:
        raise ValueError("Slack message ts is required")

    parts = ts_raw.split(".", 1)
    sec = int(parts[0]) if parts[0].isdigit() else int(float(ts_raw))
    timestamp = datetime.fromtimestamp(sec, tz=timezone.utc)

    text = str(message.get("text") or "")
    user = str(message.get("user") or message.get("bot_id") or "")
    channel = channel_id or str(message.get("channel") or "")

    external_id = f"{channel}:{ts_raw}" if channel else ts_raw
    preview_parts = [part for part in [channel, user, text] if part]
    preview = " | ".join(preview_parts)

    return {
        "eventId": f"slack-message-{external_id}",
        "tenantId": tenant_id,
        "sourceType": "slack",
        "externalId": external_id,
        "timestamp": timestamp.isoformat(),
        "payload": {
            "text": preview,
            # Stable per-channel anchor for thread grouping -- NOT external_id,
            # which is unique per message and would put every message in its
            # own "thread". See Sprint 31 board.
            "identifier": channel,
            "channel": channel,
            "sender": user,
            "message_ts": ts_raw,
        },
        "schemaVersion": "1.0.0",
    }


def send_slack_reply(*, token: str, external_id: str, text: str) -> dict[str, Any]:
    channel, _, thread_ts = external_id.partition(":")
    if not channel:
        raise ValueError("Slack external_id must be in 'channel:ts' format")

    body: dict[str, Any] = {"channel": channel, "text": text}
    if thread_ts:
        body["thread_ts"] = thread_ts

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            "https://slack.com/api/chat.postMessage",
            json=body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "allino-backend",
            },
        )
        resp.raise_for_status()
        payload = resp.json()

    if not payload.get("ok"):
        raise RuntimeError(f"Slack API error: {payload.get('error', 'unknown')}")
    return payload


class SlackConnector(BaseConnector):
    def __init__(
        self,
        tenant_id: str,
        token: str | None = None,
        channel_id: str | None = None,
        retry_policy: RetryPolicy | None = None,
        seeded_messages: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(source="slack", retry_policy=retry_policy)
        self.tenant_id = tenant_id
        self.token = token or get_secret_value("ALLINO_SLACK_BOT_TOKEN")
        self.channel_id = channel_id or get_secret_value("ALLINO_SLACK_CHANNEL_ID")
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
            map_slack_message_to_unified_event(item, tenant_id=self.tenant_id, channel_id=self.channel_id)
            for item in sliced
        ]

    def _fetch_messages_from_api(self) -> list[dict[str, Any]]:
        if not self.token or not self.channel_id:
            return []

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://slack.com/api/conversations.history",
                params={"channel": self.channel_id, "limit": 50},
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
            messages = payload.get("messages") or []
            if not isinstance(messages, list):
                return []
            return [item for item in messages if isinstance(item, dict)]
