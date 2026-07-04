from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class UnifiedEvent(BaseModel):
	model_config = ConfigDict(extra="forbid")

	eventId: str
	tenantId: str
	sourceType: str
	externalId: str
	timestamp: datetime
	payload: dict
	schemaVersion: str


class InboxMessage(BaseModel):
	event_id: str
	tenant_id: str
	source: str
	external_id: str
	timestamp: datetime
	preview: str
	thread_key: str = ""
	priority: Literal["high", "medium", "normal"] = "normal"
	reply_target: str | None = None
	archived_at: datetime | None = None
	snoozed_until: datetime | None = None
	# Opt-in ("click to load") media attachment. attachment_ref is a source-specific
	# pointer (e.g. a Rocket.Chat file id), never a directly-browsable URL -- see
	# api/ingestion.py's attachment proxy endpoint for why.
	attachment_ref: str | None = None
	attachment_type: Literal["image", "video", "file"] | None = None
	# Original filename, shown for generic "file" attachments (e.g. source code,
	# documents) so the user knows what was shared without downloading it first.
	attachment_name: str | None = None
	# Size in bytes, shown alongside attachment_name for the same reason.
	attachment_size: int | None = None
	# Channel-browser grouping (Sprint 32): only chat-shaped sources set these.
	channel_kind: Literal["team", "channel", "dm"] | None = None
	channel_team: str | None = None
