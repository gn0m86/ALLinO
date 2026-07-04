from typing import Any

from ..db.repositories.messages_repo import digest_messages
from ..domain.events import InboxMessage

# How many high-priority items to surface as "highlights" -- a stand-up digest
# is meant to be skimmed in under a minute, not a full re-listing of the inbox.
_HIGHLIGHT_LIMIT = 10


def build_digest(tenant_id: str, since_hours: int = 24) -> dict[str, Any]:
    messages: list[InboxMessage] = digest_messages(tenant_id, since_hours=since_hours)

    by_source: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for message in messages:
        by_source[message.source] = by_source.get(message.source, 0) + 1
        by_priority[message.priority] = by_priority.get(message.priority, 0) + 1

    highlights = [m for m in messages if m.priority == "high"][:_HIGHLIGHT_LIMIT]

    return {
        "tenant_id": tenant_id,
        "since_hours": since_hours,
        "total": len(messages),
        "by_source": by_source,
        "by_priority": by_priority,
        "highlights": highlights,
    }
