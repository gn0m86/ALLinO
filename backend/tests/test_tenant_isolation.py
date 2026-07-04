from datetime import datetime, timezone

from app.db import session
from app.db.repositories.audit_repo import append_audit, list_audit
from app.db.repositories.messages_repo import add_if_new, list_messages
from app.db.session import init_db
from app.domain.events import InboxMessage


def test_tenant_scoped_reads_isolate_data(tmp_path) -> None:
	session.DB_PATH = tmp_path / "tenant_isolation.db"
	init_db()

	msg_a = InboxMessage(
		event_id="evt-a",
		tenant_id="tenant_a",
		source="mock",
		external_id="ext-a",
		timestamp=datetime.now(timezone.utc),
		preview="hello a",
	)
	msg_b = InboxMessage(
		event_id="evt-b",
		tenant_id="tenant_b",
		source="mock",
		external_id="ext-b",
		timestamp=datetime.now(timezone.utc),
		preview="hello b",
	)

	assert add_if_new("dedup-a", msg_a)
	assert add_if_new("dedup-b", msg_b)

	append_audit(tenant_id="tenant_a", action="test.a")
	append_audit(tenant_id="tenant_b", action="test.b")

	inbox_a = list_messages(tenant_id="tenant_a", limit=10)
	inbox_b = list_messages(tenant_id="tenant_b", limit=10)
	audit_a = list_audit(tenant_id="tenant_a", limit=10)
	audit_b = list_audit(tenant_id="tenant_b", limit=10)

	assert len(inbox_a) == 1
	assert len(inbox_b) == 1
	assert inbox_a[0].tenant_id == "tenant_a"
	assert inbox_b[0].tenant_id == "tenant_b"

	assert len(audit_a) == 1
	assert len(audit_b) == 1
	assert audit_a[0]["tenant_id"] == "tenant_a"
	assert audit_b[0]["tenant_id"] == "tenant_b"
