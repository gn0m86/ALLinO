import base64
import json
from datetime import datetime, timedelta, timezone
from typing import List

from ...core.crypto import decrypt_text, encrypt_text
from ...domain.events import InboxMessage
from ..session import get_connection


def _encode_cursor(timestamp: str, event_id: str) -> str:
	payload = {"t": timestamp, "e": event_id}
	raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
	return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, str]:
	padding = "=" * (-len(cursor) % 4)
	raw = base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
	payload = json.loads(raw.decode("utf-8"))
	if not isinstance(payload, dict):
		raise ValueError("cursor payload must be an object")
	timestamp = payload.get("t")
	event_id = payload.get("e")
	if not isinstance(timestamp, str) or not timestamp:
		raise ValueError("cursor timestamp is missing")
	if not isinstance(event_id, str) or not event_id:
		raise ValueError("cursor event id is missing")
	return timestamp, event_id


def _map_rows(rows) -> List[InboxMessage]:
	return [
		InboxMessage(
			event_id=row["event_id"],
			tenant_id=row["tenant_id"],
			source=row["source"],
			external_id=row["external_id"],
			timestamp=row["timestamp"],
			preview=decrypt_text(row["preview"]) or "",
			thread_key=row["thread_key"] or "",
			priority=row["priority"] or "normal",
			reply_target=decrypt_text(row["reply_target"]),
			archived_at=row["archived_at"],
			snoozed_until=row["snoozed_until"],
			attachment_ref=row["attachment_ref"],
			attachment_type=row["attachment_type"],
			attachment_name=row["attachment_name"],
			attachment_size=row["attachment_size"],
			channel_kind=row["channel_kind"],
			channel_team=row["channel_team"],
		)
		for row in rows
	]


def add_if_new(dedup_hash: str, message: InboxMessage) -> bool:
	with get_connection() as conn:
		cursor = conn.execute(
			"""
			INSERT OR IGNORE INTO messages (
				dedup_hash,
				event_id,
				tenant_id,
				source,
				external_id,
				timestamp,
				preview,
				thread_key,
				priority,
				reply_target,
				attachment_ref,
				attachment_type,
				attachment_name,
				attachment_size,
				channel_kind,
				channel_team
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			""",
			(
				dedup_hash,
				message.event_id,
				message.tenant_id,
				message.source,
				message.external_id,
				message.timestamp.isoformat(),
				encrypt_text(message.preview),
				message.thread_key,
				message.priority,
				encrypt_text(message.reply_target),
				message.attachment_ref,
				message.attachment_type,
				message.attachment_name,
				message.attachment_size,
				message.channel_kind,
				message.channel_team,
			),
		)
		conn.commit()
		return cursor.rowcount > 0


_ACTIVE_FILTER = "AND archived_at IS NULL AND (snoozed_until IS NULL OR snoozed_until <= ?)"


def get_message(tenant_id: str, event_id: str) -> InboxMessage | None:
	with get_connection() as conn:
		row = conn.execute(
			"""
			SELECT event_id, tenant_id, source, external_id, timestamp, preview, thread_key, priority,
			       reply_target, archived_at, snoozed_until, attachment_ref, attachment_type, attachment_name, attachment_size,
			       channel_kind, channel_team
			FROM messages
			WHERE tenant_id = ? AND event_id = ?
			""",
			(tenant_id, event_id),
		).fetchone()
	if row is None:
		return None
	return _map_rows([row])[0]


def list_messages(
	tenant_id: str,
	limit: int = 100,
	cursor: str | None = None,
	archived_only: bool = False,
) -> List[InboxMessage]:
	now = datetime.now(timezone.utc).isoformat()
	state_filter = "AND archived_at IS NOT NULL" if archived_only else _ACTIVE_FILTER
	# archived_only ignores `now` entirely (no snoozed_until comparison needed for that
	# branch) but keeping a single param tuple shape below is simpler than branching twice.
	state_param: tuple = () if archived_only else (now,)

	with get_connection() as conn:
		if cursor:
			timestamp, event_id = _decode_cursor(cursor)
			rows = conn.execute(
				f"""
				SELECT event_id, tenant_id, source, external_id, timestamp, preview, thread_key, priority,
				       reply_target, archived_at, snoozed_until, attachment_ref, attachment_type, attachment_name, attachment_size,
			       channel_kind, channel_team
				FROM messages
				WHERE tenant_id = ?
				  AND (
				      timestamp < ?
				      OR (timestamp = ? AND event_id < ?)
				  )
				  {state_filter}
				ORDER BY timestamp DESC, event_id DESC
				LIMIT ?
				""",
				(tenant_id, timestamp, timestamp, event_id, *state_param, limit),
			).fetchall()
		else:
			rows = conn.execute(
				f"""
				SELECT event_id, tenant_id, source, external_id, timestamp, preview, thread_key, priority,
				       reply_target, archived_at, snoozed_until, attachment_ref, attachment_type, attachment_name, attachment_size,
			       channel_kind, channel_team
				FROM messages
				WHERE tenant_id = ?
				  {state_filter}
				ORDER BY timestamp DESC, event_id DESC
				LIMIT ?
				""",
				(tenant_id, *state_param, limit),
			).fetchall()

	return _map_rows(rows)


def list_messages_page(
	tenant_id: str,
	limit: int = 100,
	cursor: str | None = None,
	archived_only: bool = False,
) -> tuple[List[InboxMessage], str | None]:
	messages = list_messages(tenant_id=tenant_id, limit=limit, cursor=cursor, archived_only=archived_only)
	if len(messages) < limit:
		return messages, None
	last = messages[-1]
	timestamp = last.timestamp.isoformat() if hasattr(last.timestamp, "isoformat") else str(last.timestamp)
	return messages, _encode_cursor(timestamp, last.event_id)


# How many of the tenant's most-recent active messages a search scans through.
# `preview` is encrypted at rest (CLAUDE.md security gate), so it can't be indexed
# for a real database-level text search -- this decrypts a bounded, recency-ordered
# window and matches in Python instead. Exact (case-insensitive substring) matching
# only, no fuzzy/stemmed matching. Fine at local-first, single-tenant scale; if a
# tenant's active message volume ever exceeds this, that's the trigger to revisit
# (a real FTS index would mean deciding to store a plaintext-searchable copy of
# preview text, a real security tradeoff -- not something to default into silently).
_SEARCH_SCAN_LIMIT = 5000


def search_messages(tenant_id: str, query: str, limit: int = 50) -> List[InboxMessage]:
	needle = query.strip().lower()
	if not needle:
		return []

	now = datetime.now(timezone.utc).isoformat()
	with get_connection() as conn:
		rows = conn.execute(
			f"""
			SELECT event_id, tenant_id, source, external_id, timestamp, preview, thread_key, priority,
			       reply_target, archived_at, snoozed_until, attachment_ref, attachment_type, attachment_name, attachment_size,
			       channel_kind, channel_team
			FROM messages
			WHERE tenant_id = ?
			  {_ACTIVE_FILTER}
			ORDER BY timestamp DESC, event_id DESC
			LIMIT ?
			""",
			(tenant_id, now, _SEARCH_SCAN_LIMIT),
		).fetchall()

	candidates = _map_rows(rows)
	matches = [
		m
		for m in candidates
		if needle in m.external_id.lower()
		or needle in (m.preview or "").lower()
		or needle in m.source.lower()
	]
	return matches[:limit]


def list_thread_summaries(tenant_id: str, source: str | None = None) -> List[InboxMessage]:
	"""Latest active message per thread, for chat-shaped sources only (channel_kind
	IS NOT NULL) -- the channel-browser view's "one row per channel" list."""
	now = datetime.now(timezone.utc).isoformat()
	source_filter = "AND source = ?" if source else ""
	params: list = [tenant_id]
	if source:
		params.append(source)
	params.append(now)

	with get_connection() as conn:
		rows = conn.execute(
			f"""
			SELECT * FROM (
				SELECT event_id, tenant_id, source, external_id, timestamp, preview, thread_key, priority,
				       reply_target, archived_at, snoozed_until, attachment_ref, attachment_type, attachment_name, attachment_size,
				       channel_kind, channel_team,
				       ROW_NUMBER() OVER (PARTITION BY thread_key ORDER BY timestamp DESC, event_id DESC) AS rn
				FROM messages
				WHERE tenant_id = ?
				  AND channel_kind IS NOT NULL
				  {source_filter}
				  AND archived_at IS NULL AND (snoozed_until IS NULL OR snoozed_until <= ?)
			)
			WHERE rn = 1
			ORDER BY timestamp DESC
			""",
			params,
		).fetchall()
	return _map_rows(rows)


def list_thread_messages(tenant_id: str, thread_key: str, limit: int = 500) -> List[InboxMessage]:
	"""Every active message in one thread (channel/DM), oldest first -- the
	channel-browser view's chat-transcript order (matches Telegram/Rocket.Chat:
	scroll up for history, newest message at the bottom)."""
	now = datetime.now(timezone.utc).isoformat()
	with get_connection() as conn:
		rows = conn.execute(
			f"""
			SELECT event_id, tenant_id, source, external_id, timestamp, preview, thread_key, priority,
			       reply_target, archived_at, snoozed_until, attachment_ref, attachment_type, attachment_name, attachment_size,
			       channel_kind, channel_team
			FROM messages
			WHERE tenant_id = ? AND thread_key = ?
			  {_ACTIVE_FILTER}
			ORDER BY timestamp ASC, event_id ASC
			LIMIT ?
			""",
			(tenant_id, thread_key, now, limit),
		).fetchall()
	return _map_rows(rows)


def digest_messages(tenant_id: str, since_hours: int = 24) -> List[InboxMessage]:
	"""Active messages ingested in the last `since_hours`, for the activity digest.
	Uses `created_at` (server ingestion time) rather than `timestamp` (the source
	event's own time) -- a re-synced old event shouldn't show up as "new since
	last check"."""
	since = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
	now = datetime.now(timezone.utc).isoformat()
	with get_connection() as conn:
		rows = conn.execute(
			f"""
			SELECT event_id, tenant_id, source, external_id, timestamp, preview, thread_key, priority,
			       reply_target, archived_at, snoozed_until, attachment_ref, attachment_type, attachment_name, attachment_size,
			       channel_kind, channel_team
			FROM messages
			WHERE tenant_id = ?
			  AND created_at >= ?
			  {_ACTIVE_FILTER}
			ORDER BY timestamp DESC, event_id DESC
			""",
			(tenant_id, since, now),
		).fetchall()
	return _map_rows(rows)


def delete_all_messages(tenant_id: str) -> int:
	"""Hard-delete every message row for a tenant, regardless of archived/snoozed
	state -- a full wipe of message data. Scoped to `messages` only; does not
	touch outbound_replies, connectors, or the append-only audit trail."""
	with get_connection() as conn:
		cursor = conn.execute("DELETE FROM messages WHERE tenant_id = ?", (tenant_id,))
		conn.commit()
		return cursor.rowcount


def count_messages(tenant_id: str) -> int:
	with get_connection() as conn:
		row = conn.execute(
			"SELECT COUNT(*) AS c FROM messages WHERE tenant_id = ?",
			(tenant_id,),
		).fetchone()
		return int(row["c"])


def archive_message(tenant_id: str, event_id: str) -> bool:
	with get_connection() as conn:
		cursor = conn.execute(
			"UPDATE messages SET archived_at = ? WHERE tenant_id = ? AND event_id = ?",
			(datetime.now(timezone.utc).isoformat(), tenant_id, event_id),
		)
		conn.commit()
		return cursor.rowcount > 0


def unarchive_message(tenant_id: str, event_id: str) -> bool:
	with get_connection() as conn:
		cursor = conn.execute(
			"UPDATE messages SET archived_at = NULL WHERE tenant_id = ? AND event_id = ?",
			(tenant_id, event_id),
		)
		conn.commit()
		return cursor.rowcount > 0


def snooze_message(tenant_id: str, event_id: str, snoozed_until: str) -> bool:
	with get_connection() as conn:
		cursor = conn.execute(
			"UPDATE messages SET snoozed_until = ? WHERE tenant_id = ? AND event_id = ?",
			(snoozed_until, tenant_id, event_id),
		)
		conn.commit()
		return cursor.rowcount > 0
