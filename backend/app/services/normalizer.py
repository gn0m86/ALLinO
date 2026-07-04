import hashlib
import re

from ..domain.events import InboxMessage, UnifiedEvent
from .priority_classifier import classify_priority


def _normalized_text_fragment(value: object, max_len: int = 80) -> str:
	if not isinstance(value, str):
		return ""
	collapsed = re.sub(r"\s+", " ", value).strip().lower()
	if not collapsed:
		return ""
	return collapsed[:max_len]


def _semantic_anchor_from_payload(payload: dict) -> str:
	parts: list[str] = []
	for key in ("repository", "project", "team", "subject_type", "target_type", "state", "action_name", "reason"):
		value = payload.get(key)
		if isinstance(value, str) and value.strip():
			parts.append(f"{key}:{value.strip().lower()}")

	text_fragment = _normalized_text_fragment(payload.get("text"))
	if text_fragment and not parts:
		parts.append(f"text:{text_fragment}")

	return "|".join(parts)


def _compute_thread_key(event: UnifiedEvent) -> str:
	payload = event.payload if isinstance(event.payload, dict) else {}
	strong_anchors = [
		payload.get("subject_url"),
		payload.get("target_url"),
		payload.get("url"),
		payload.get("identifier"),
	]

	anchor = ""
	for candidate in strong_anchors:
		if isinstance(candidate, str) and candidate.strip():
			anchor = candidate.strip().lower()
			break

	if not anchor:
		anchor = _semantic_anchor_from_payload(payload)

	if not anchor:
		parts = [p for p in event.externalId.lower().replace("_", "-").split("-") if p]
		anchor = "-".join(parts[:2]) if parts else event.externalId.lower()

	seed = f"{event.tenantId}|{event.sourceType.lower()}|{anchor}"
	return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def _reply_target(event: UnifiedEvent) -> str | None:
	payload = event.payload if isinstance(event.payload, dict) else {}
	source = event.sourceType.lower()
	if source == "github":
		value = payload.get("subject_url")
	elif source == "gitlab":
		value = payload.get("target_url")
	elif source == "rocketchat":
		# Not an address to reply to here (unlike github/gitlab's use of this same
		# field) -- the id of the Rocket.Chat thread-root message this one is a
		# reply within, so the frontend can show a "replying in thread" quote.
		# See map_rocketchat_message_to_unified_event's reply_to_message_id.
		value = payload.get("reply_to_message_id")
	else:
		return None
	return value.strip() if isinstance(value, str) and value.strip() else None


def normalize_event(event: UnifiedEvent) -> InboxMessage:
	preview = ""
	attachment_ref: str | None = None
	attachment_type: str | None = None
	attachment_name: str | None = None
	attachment_size: int | None = None
	channel_kind: str | None = None
	channel_team: str | None = None
	if isinstance(event.payload, dict):
		value = event.payload.get("text") or event.payload.get("message") or ""
		preview = str(value)
		ref = event.payload.get("attachment_ref")
		atype = event.payload.get("attachment_type")
		if isinstance(ref, str) and ref.strip() and atype in ("image", "video", "file"):
			attachment_ref = ref.strip()
			attachment_type = atype
			name = event.payload.get("attachment_name")
			if isinstance(name, str) and name.strip():
				attachment_name = name.strip()
			size = event.payload.get("attachment_size")
			if isinstance(size, (int, float)) and not isinstance(size, bool) and size >= 0:
				attachment_size = int(size)
		kind = event.payload.get("channel_kind")
		if kind in ("team", "channel", "dm"):
			channel_kind = kind
		team = event.payload.get("channel_team")
		if isinstance(team, str) and team.strip():
			channel_team = team.strip()

	return InboxMessage(
		event_id=event.eventId,
		tenant_id=event.tenantId,
		source=event.sourceType,
		external_id=event.externalId,
		timestamp=event.timestamp,
		preview=preview,
		thread_key=_compute_thread_key(event),
		priority=classify_priority(event),
		reply_target=_reply_target(event),
		attachment_ref=attachment_ref,
		attachment_type=attachment_type,
		attachment_name=attachment_name,
		attachment_size=attachment_size,
		channel_kind=channel_kind,
		channel_team=channel_team,
	)
