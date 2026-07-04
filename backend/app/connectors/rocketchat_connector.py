from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from ..core.secrets import get_secret_value
from .base import BaseConnector, ConnectorHealth, RetryPolicy

# Rocket.Chat message bodies are markdown -- most of it renders fine as plain
# text, but [label](url) links (often auto-generated "jump to message" links
# with an empty label, e.g. from quote/reply) show up as raw noise otherwise.
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def _strip_markdown_links(text: str) -> str:
    def _replace(match: "re.Match[str]") -> str:
        label = match.group(1).strip()
        return label if label else ""

    return _MARKDOWN_LINK_RE.sub(_replace, text)

# Rocket.Chat's REST API splits "list messages" by room type -- there's no single
# endpoint that works across public channels, private groups, and DMs.
_ROOM_TYPE_MESSAGE_ENDPOINTS = {
    "c": "channels.messages",
    "p": "groups.messages",
    "d": "im.messages",
}

# Likewise for "room info" (used to detect Team membership -- subscriptions.get
# doesn't expose teamMain/teamId, only channels.info/groups.info do).
_ROOM_TYPE_INFO_ENDPOINTS = {
    "c": "channels.info",
    "p": "groups.info",
}
_ROOM_TYPE_INFO_KEYS = {
    "c": "channel",
    "p": "group",
}

# Small delay between per-room requests in "all rooms" mode -- a user in many
# channels/DMs otherwise fires a burst of requests in quick succession, which
# self-hosted Rocket.Chat servers commonly rate-limit (429) by default.
_ROOM_FETCH_DELAY_SECONDS = 0.5

# Fallback cooldown when a room hits 429 and the server doesn't send a
# Retry-After header telling us exactly how long to wait.
_DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS = 5.0


def _parse_retry_after(value: str | None) -> float:
    if value is None:
        return _DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS
    try:
        return max(float(value), 0.0)
    except ValueError:
        return _DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS


def _extract_attachment(message: dict[str, Any]) -> tuple[str | None, str | None, str | None, int | None]:
    """Returns (attachment_ref, attachment_type, attachment_name, attachment_size)
    for the first file on a message, or (None, None, None, None). Images/videos
    get their own inline viewer; anything else (source files, documents,
    archives -- very common in the dev-team channels this connector was built
    for) still needs to show up as a generic downloadable "file" attachment
    rather than silently vanishing, which is what happened before this type
    existed. attachment_ref is Rocket.Chat's internal file id -- never a
    directly-browsable URL, since fetching it needs the connector's own auth
    headers (see the attachment proxy endpoint in api/attachments.py)."""
    file_info = message.get("file")
    if not isinstance(file_info, dict):
        files = message.get("files")
        file_info = files[0] if isinstance(files, list) and files and isinstance(files[0], dict) else None
    if not isinstance(file_info, dict):
        return None, None, None, None

    file_id = str(file_info.get("_id") or "")
    mime_type = str(file_info.get("type") or "")
    name = file_info.get("name")
    filename = str(name) if name else None
    size = file_info.get("size")
    file_size = int(size) if isinstance(size, (int, float)) else None
    if not file_id:
        return None, None, None, None

    if mime_type.startswith("image/"):
        return file_id, "image", filename, file_size
    if mime_type.startswith("video/"):
        return file_id, "video", filename, file_size
    return file_id, "file", filename, file_size


def map_rocketchat_message_to_unified_event(
    message: dict[str, Any],
    *,
    tenant_id: str,
    channel_id: str | None = None,
    channel_name: str | None = None,
    channel_kind: str | None = None,
    channel_team: str | None = None,
) -> dict[str, Any]:
    message_id = str(message.get("_id") or "")
    if not message_id:
        raise ValueError("Rocket.Chat message id is required")

    ts_raw = message.get("ts")
    if isinstance(ts_raw, str):
        timestamp = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    else:
        timestamp = datetime.now(timezone.utc)

    content = _strip_markdown_links(str(message.get("msg") or "")).strip()
    sender_obj = message.get("u") or {}
    # Prefer the display name (matches the channel list's own naming, which reads
    # subscriptions.get's fname the same way) over the technical username --
    # falls back to username for bots/system messages that only set one.
    sender = str(sender_obj.get("name") or sender_obj.get("username") or sender_obj.get("_id") or "")
    room_id = channel_id or str(message.get("rid") or "")
    # Prefer the human-readable room name (from subscriptions.get) for display --
    # falls back to the raw room id, which is all we have in single-room mode.
    room_display = channel_name or room_id

    external_id = f"{room_id}:{message_id}" if room_id else message_id
    # Rocket.Chat threads are flat: every reply in a thread carries the SAME tmid
    # -- the thread's root message id, not a chain of individual reply pointers.
    # Good enough to show "replying in thread started by X" against the root.
    thread_root_id = message.get("tmid")
    reply_to_message_id = str(thread_root_id) if thread_root_id else None
    attachment_ref, attachment_type, attachment_name, attachment_size = _extract_attachment(message)
    preview_parts = [part for part in [room_display, sender, content] if part]
    if not content and attachment_type:
        label = f"[{attachment_name}]" if attachment_name else f"[{attachment_type}]"
        preview_parts = [room_display, sender, label]
    preview = " | ".join(p for p in preview_parts if p)

    return {
        "eventId": f"rocketchat-message-{external_id}",
        "tenantId": tenant_id,
        "sourceType": "rocketchat",
        "externalId": external_id,
        "timestamp": timestamp.isoformat(),
        "payload": {
            "text": preview,
            # Stable per-room anchor used for thread grouping -- deliberately NOT
            # external_id (unique per message), which would put every message in
            # its own thread. See Sprint 31 board for the full story: this bug
            # also existed in Slack/Discord/Teams/Telegram, fixed the same way.
            "identifier": room_id,
            "channel": room_display,
            "sender": sender,
            "message_id": message_id,
            "attachment_ref": attachment_ref,
            "attachment_type": attachment_type,
            "attachment_name": attachment_name,
            "attachment_size": attachment_size,
            "reply_to_message_id": reply_to_message_id,
            # Channel-browser grouping (Sprint 32) -- see channel_kind's docstring
            # on InboxMessage for what "team"/"channel"/"dm" mean here.
            "channel_kind": channel_kind or "channel",
            "channel_team": channel_team,
        },
        "schemaVersion": "1.0.0",
    }


def send_rocketchat_reply(*, token: str, external_id: str, text: str) -> dict[str, Any]:
    channel, _, message_id = external_id.partition(":")
    if not channel:
        raise ValueError("Rocket.Chat external_id must be in 'channel:message_id' format")

    user_id = get_secret_value("ALLINO_ROCKETCHAT_USER_ID")
    base_url = (os.getenv("ALLINO_ROCKETCHAT_BASE_URL") or "").rstrip("/")
    if not user_id or not base_url:
        raise RuntimeError(
            "Rocket.Chat reply requires ALLINO_ROCKETCHAT_USER_ID and ALLINO_ROCKETCHAT_BASE_URL"
        )

    # tmid makes this a genuine Rocket.Chat threaded reply to the specific message
    # the user picked, not just a new message dropped into the room -- every
    # rocketchat InboxMessage's external_id carries its own message id (see
    # map_rocketchat_message_to_unified_event), so this works for any message.
    body: dict[str, Any] = {"roomId": channel, "text": text}
    if message_id:
        body["tmid"] = message_id

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"{base_url}/api/v1/chat.postMessage",
            json=body,
            headers={
                "Accept": "application/json",
                "X-Auth-Token": token,
                "X-User-Id": user_id,
                "User-Agent": "allino-backend",
            },
        )
        resp.raise_for_status()
        payload = resp.json()

    if not payload.get("success"):
        raise RuntimeError(f"Rocket.Chat API error: {payload.get('error', 'unknown')}")
    return payload


def get_own_rocketchat_username(*, token: str, user_id: str, base_url: str) -> str | None:
    """The display name of the configured Rocket.Chat account itself (via
    /api/v1/me). Used by the frontend to tell "my own messages" apart from
    everyone else's in a transcript -- every message's sender is now stored as
    a display name too (see map_rocketchat_message_to_unified_event's sender
    extraction, which prefers u.name over u.username), so a plain string
    comparison against this value is enough. Not a secret -- a name is already
    visible in every message this account posts."""
    base_url = base_url.rstrip("/")
    headers = {"X-Auth-Token": token, "X-User-Id": user_id, "User-Agent": "allino-backend"}

    with httpx.Client(timeout=10.0) as client:
        try:
            resp = client.get(f"{base_url}/api/v1/me", headers=headers)
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError:
            return None

    if not isinstance(payload, dict):
        return None
    display_name = payload.get("name") or payload.get("username")
    return str(display_name) if display_name else None


def get_dm_counterpart_utc_offset(*, token: str, user_id: str, base_url: str, room_id: str) -> int | None:
    """Best-effort lookup of a DM counterpart's Rocket.Chat utcOffset (a plain
    number of hours, DST already folded in server-side at request time -- not a
    full IANA zone), so the frontend can show their local time next to yours.
    Only meaningful for direct messages: group channels/teams have no single
    "counterpart". Returns None for anything else, or if either API call fails
    -- this is a display nicety, never worth failing the caller over."""
    base_url = base_url.rstrip("/")
    headers = {"X-Auth-Token": token, "X-User-Id": user_id, "User-Agent": "allino-backend"}

    with httpx.Client(timeout=10.0) as client:
        try:
            resp = client.get(f"{base_url}/api/v1/subscriptions.get", headers=headers)
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError:
            return None

        subscriptions = payload.get("update", []) if isinstance(payload, dict) else []
        match = next(
            (s for s in subscriptions if isinstance(s, dict) and s.get("rid") == room_id and s.get("t") == "d"),
            None,
        )
        username = match.get("name") if match else None
        if not username:
            return None

        try:
            resp = client.get(
                f"{base_url}/api/v1/users.info",
                params={"username": username},
                headers=headers,
            )
            resp.raise_for_status()
            user_payload = resp.json()
        except httpx.HTTPError:
            return None

    user_info = user_payload.get("user") if isinstance(user_payload, dict) else None
    offset = user_info.get("utcOffset") if isinstance(user_info, dict) else None
    return int(offset) if isinstance(offset, (int, float)) else None


class RocketChatConnector(BaseConnector):
    def __init__(
        self,
        tenant_id: str,
        token: str | None = None,
        user_id: str | None = None,
        base_url: str | None = None,
        channel_id: str | None = None,
        retry_policy: RetryPolicy | None = None,
        seeded_messages: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(source="rocketchat", retry_policy=retry_policy)
        self.tenant_id = tenant_id
        self.token = token or get_secret_value("ALLINO_ROCKETCHAT_TOKEN")
        self.user_id = user_id or get_secret_value("ALLINO_ROCKETCHAT_USER_ID")
        self.base_url = (base_url or os.getenv("ALLINO_ROCKETCHAT_BASE_URL") or "").rstrip("/")
        self.channel_id = channel_id or get_secret_value("ALLINO_ROCKETCHAT_CHANNEL_ID")
        self._started = False
        self._seeded_messages = seeded_messages or []

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health(self) -> ConnectorHealth:
        if not self._started:
            status = "stopped"
        elif (self.token and self.user_id and self.base_url) or self._seeded_messages:
            status = "healthy"
        else:
            status = "degraded"

        return ConnectorHealth(
            status=status,
            source=self.source,
            details={
                "has_token": bool(self.token and self.user_id),
                "base_url": self.base_url,
                # None means "all rooms the user belongs to" (via subscriptions.get),
                # not "misconfigured" -- see fetch_events/_fetch_messages_from_api.
                "channel_id": self.channel_id,
                "seeded_messages": len(self._seeded_messages),
                "retry_count": self.last_retry_count,
            },
        )

    def fetch_events(self, cursor: str | None = None) -> Iterable[dict[str, Any]]:
        if not self._started:
            return []

        messages = self._seeded_messages
        if not messages and self.token and self.user_id and self.base_url:
            messages = self.run_with_retry(self._fetch_messages_from_api)

        start_idx = int(cursor) if cursor else 0
        sliced = messages[start_idx:]
        return [
            # channel_id=None here is intentional in "all rooms" mode -- each
            # message already carries its own room id ("rid"), which
            # map_rocketchat_message_to_unified_event falls back to. The _room_*
            # keys (attached in _fetch_messages_from_api, "all rooms" mode only)
            # are popped off here so they don't leak into the unified event payload.
            map_rocketchat_message_to_unified_event(
                item,
                tenant_id=self.tenant_id,
                channel_id=self.channel_id,
                channel_name=item.pop("_room_name", None),
                channel_kind=item.pop("_room_kind", None),
                channel_team=item.pop("_room_team", None),
            )
            for item in sliced
        ]

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "X-Auth-Token": self.token or "",
            "X-User-Id": self.user_id or "",
            "User-Agent": "allino-backend",
        }

    def _list_subscriptions(self, client: httpx.Client) -> list[dict[str, Any]]:
        """Every room (channel, private group, or DM) this user belongs to --
        used for "watch everything" mode when no single channel_id is configured.
        Needs no admin rights: subscriptions.get only ever returns the calling
        user's own subscriptions."""
        resp = client.get(f"{self.base_url}/api/v1/subscriptions.get", headers=self._auth_headers())
        resp.raise_for_status()
        payload = resp.json()
        subscriptions = payload.get("update") if isinstance(payload, dict) else None
        return [s for s in (subscriptions or []) if isinstance(s, dict)]

    def _get_room_messages_once(self, client: httpx.Client, endpoint: str, room_id: str) -> list[dict[str, Any]]:
        resp = client.get(
            f"{self.base_url}/api/v1/{endpoint}",
            params={"roomId": room_id, "count": 50},
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        payload = resp.json()
        messages = payload.get("messages") if isinstance(payload, dict) else None
        if not isinstance(messages, list):
            return []
        return [item for item in messages if isinstance(item, dict)]

    def _fetch_room_kind(self, client: httpx.Client, room_id: str, room_type: str) -> tuple[str, str | None]:
        """("dm", None) for direct messages; otherwise ("team", team_name) if this
        room is a Team's main channel (teamMain), else ("channel", None). Needs an
        extra request per channel/group room -- subscriptions.get doesn't expose
        teamMain/teamId, only channels.info/groups.info do. Best-effort: any error
        here just falls back to "channel" rather than failing the whole sync."""
        if room_type == "d":
            return "dm", None

        endpoint = _ROOM_TYPE_INFO_ENDPOINTS.get(room_type)
        info_key = _ROOM_TYPE_INFO_KEYS.get(room_type)
        if not endpoint or not info_key:
            return "channel", None

        try:
            resp = client.get(
                f"{self.base_url}/api/v1/{endpoint}",
                params={"roomId": room_id},
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPStatusError:
            return "channel", None

        room_info = payload.get(info_key) if isinstance(payload, dict) else None
        if not isinstance(room_info, dict):
            return "channel", None
        if room_info.get("teamMain"):
            team_name = room_info.get("fname") or room_info.get("name")
            return "team", str(team_name) if team_name else None
        return "channel", None

    def _fetch_room_messages(self, client: httpx.Client, room_id: str, room_type: str) -> list[dict[str, Any]]:
        endpoint = _ROOM_TYPE_MESSAGE_ENDPOINTS.get(room_type)
        if not endpoint:
            return []
        try:
            return self._get_room_messages_once(client, endpoint, room_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 429:
                raise
            time.sleep(_parse_retry_after(exc.response.headers.get("Retry-After")))
            try:
                return self._get_room_messages_once(client, endpoint, room_id)
            except httpx.HTTPStatusError as retry_exc:
                if retry_exc.response.status_code != 429:
                    raise
                # Give up on this one room rather than failing the whole "all
                # rooms" sync -- one persistently rate-limited room shouldn't
                # hide messages from every other room that would have worked.
                return []

    def _fetch_messages_from_api(self) -> list[dict[str, Any]]:
        if not self.token or not self.user_id or not self.base_url:
            return []

        with httpx.Client(timeout=10.0) as client:
            if self.channel_id:
                return self._fetch_room_messages(client, self.channel_id, "c")

            all_messages: list[dict[str, Any]] = []
            subscriptions = self._list_subscriptions(client)
            for index, subscription in enumerate(subscriptions):
                room_id = subscription.get("rid")
                room_type = subscription.get("t")
                if not room_id or not room_type:
                    continue
                if index > 0:
                    time.sleep(_ROOM_FETCH_DELAY_SECONDS)
                room_name = subscription.get("fname") or subscription.get("name")
                room_messages = self._fetch_room_messages(client, room_id, room_type)
                if not room_messages:
                    continue

                time.sleep(_ROOM_FETCH_DELAY_SECONDS)
                room_kind, team_name = self._fetch_room_kind(client, room_id, room_type)

                for msg in room_messages:
                    if room_name:
                        msg["_room_name"] = room_name
                    msg["_room_kind"] = room_kind
                    msg["_room_team"] = team_name
                    all_messages.append(msg)
            return all_messages
