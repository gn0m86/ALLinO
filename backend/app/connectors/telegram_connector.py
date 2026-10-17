from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from ..core.secrets import get_secret_value
from .base import BaseConnector, ConnectorHealth, RetryPolicy


def map_telegram_update_to_unified_event(
    update: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    update_id_raw = update.get("update_id")
    if update_id_raw is None:
        raise ValueError("Telegram update_id is required")

    update_id = str(update_id_raw)
    message = update.get("message") or update.get("edited_message") or {}
    if not isinstance(message, dict):
        message = {}

    message_id_raw = message.get("message_id")
    message_id = str(message_id_raw) if message_id_raw is not None else update_id

    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    chat_title = str(chat.get("title") or chat.get("username") or chat_id)
    chat_type = str(chat.get("type") or "")
    # Telegram has no "team"/workspace concept like Slack or Rocket.Chat -- a bot
    # only ever sees individual chats, so this is a two-way split (unlike
    # Rocket.Chat's team/channel/dm three-way one). See ChannelBrowser.tsx and
    # CHAT_SHAPED_SOURCES in lib/types.ts for the frontend side of this.
    if chat_type == "private":
        channel_kind: str | None = "dm"
    elif chat_type in ("group", "supergroup", "channel"):
        channel_kind = "channel"
    else:
        channel_kind = None

    text = str(message.get("text") or message.get("caption") or "")
    from_user = message.get("from") or {}
    sender = str(from_user.get("username") or from_user.get("first_name") or "")

    ts_raw = message.get("date")
    if isinstance(ts_raw, int):
        timestamp = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)

    preview_parts = [part for part in [chat_title, sender, text] if part]
    preview = " | ".join(preview_parts)

    anchor_external_id = f"{chat_id}:{message_id}" if chat_id else message_id

    return {
        "eventId": f"tg-update-{update_id}",
        "tenantId": tenant_id,
        "sourceType": "telegram",
        "externalId": anchor_external_id,
        "timestamp": timestamp.isoformat(),
        "payload": {
            "text": preview,
            "chat_id": chat_id,
            "chat_title": chat_title,
            "sender": sender,
            "message_id": message_id,
            # Stable per-chat anchor for thread grouping -- NOT
            # anchor_external_id (unique per message). See Sprint 31 board.
            "identifier": chat_id,
            "channel_kind": channel_kind,
        },
        "schemaVersion": "1.0.0",
    }


def _raise_for_status_redacted(resp: httpx.Response, token: str) -> None:
    """httpx's HTTPStatusError message embeds the full request URL, and the Bot
    API puts the bot token in the URL path -- callers persist str(exc) into
    connector status, run history and the append-only audit log, so the
    default message would leak the token there. Re-raise with it masked; still
    an HTTPStatusError so retry classification (4xx = not retryable) is unchanged."""
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise httpx.HTTPStatusError(
            str(exc).replace(token, "***"), request=exc.request, response=exc.response
        ) from None


def send_telegram_reply(*, token: str, external_id: str, text: str) -> dict[str, Any]:
    chat_id, _, message_id = external_id.partition(":")
    if not chat_id:
        raise ValueError("Telegram external_id must be in 'chat_id:message_id' format")

    body: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if message_id.isdigit():
        body["reply_to_message_id"] = int(message_id)

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=body,
            headers={"Accept": "application/json", "User-Agent": "allino-backend"},
        )
        _raise_for_status_redacted(resp, token)
        payload = resp.json()

    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload.get('description', 'unknown')}")
    return payload


class TelegramConnector(BaseConnector):
    def __init__(
        self,
        tenant_id: str,
        token: str | None = None,
        retry_policy: RetryPolicy | None = None,
        seeded_updates: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(source="telegram", retry_policy=retry_policy)
        self.tenant_id = tenant_id
        self.token = token or get_secret_value("ALLINO_TELEGRAM_BOT_TOKEN")
        self._started = False
        self._seeded_updates = seeded_updates or []

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health(self) -> ConnectorHealth:
        if not self._started:
            status = "stopped"
        elif self.token or self._seeded_updates:
            status = "healthy"
        else:
            status = "degraded"

        return ConnectorHealth(
            status=status,
            source=self.source,
            details={
                "has_token": bool(self.token),
                "seeded_updates": len(self._seeded_updates),
                "retry_count": self.last_retry_count,
            },
        )

    def fetch_events(self, cursor: str | None = None) -> Iterable[dict[str, Any]]:
        if not self._started:
            return []

        updates = self._seeded_updates
        if not updates and self.token:
            updates = self.run_with_retry(self._fetch_updates_from_api)

        start_idx = int(cursor) if cursor else 0
        sliced = updates[start_idx:]
        return [
            map_telegram_update_to_unified_event(item, tenant_id=self.tenant_id)
            for item in sliced
        ]

    def _fetch_updates_from_api(self) -> list[dict[str, Any]]:
        if not self.token:
            return []

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"https://api.telegram.org/bot{self.token}/getUpdates",
                params={"limit": 50},
                headers={
                    "Accept": "application/json",
                    "User-Agent": "allino-backend",
                },
            )
            _raise_for_status_redacted(resp, self.token)
            payload = resp.json()
            if not isinstance(payload, dict):
                return []
            results = payload.get("result") or []
            if not isinstance(results, list):
                return []
            return [item for item in results if isinstance(item, dict)]
