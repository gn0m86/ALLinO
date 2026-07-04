from fastapi.testclient import TestClient

from app.db import session
from app.main import app


def _seed_event(i: int) -> dict:
    return {
        "eventId": f"evt-{i}",
        "tenantId": "tenant_demo",
        "sourceType": "seed",
        "externalId": f"seed-{i}",
        "timestamp": f"2026-07-01T12:00:{10 + i:02d}Z",
        "payload": {"text": f"event {i}"},
        "schemaVersion": "1.0.0",
    }


def test_inbox_page_returns_next_cursor_and_next_page(tmp_path) -> None:
    session.DB_PATH = tmp_path / "inbox_cursor_page.db"

    with TestClient(app) as client:
        for i in range(5):
            r = client.post(
                "/api/v1/ingestion/events?tenant_id=tenant_demo",
                json=_seed_event(i),
            )
            assert r.status_code == 200

        first = client.get(
            "/api/v1/ingestion/inbox/page?tenant_id=tenant_demo&limit=2"
        )
        assert first.status_code == 200
        first_payload = first.json()
        assert len(first_payload["items"]) == 2
        assert first_payload["next_cursor"]

        second = client.get(
            f"/api/v1/ingestion/inbox/page?tenant_id=tenant_demo&limit=2&cursor={first_payload['next_cursor']}"
        )
        assert second.status_code == 200
        second_payload = second.json()
        assert len(second_payload["items"]) == 2

        first_ids = {item["event_id"] for item in first_payload["items"]}
        second_ids = {item["event_id"] for item in second_payload["items"]}
        assert first_ids.isdisjoint(second_ids)


def test_inbox_rejects_invalid_cursor(tmp_path) -> None:
    session.DB_PATH = tmp_path / "inbox_cursor_invalid.db"

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingestion/inbox?tenant_id=tenant_demo&cursor=invalid@@cursor"
        )

    assert response.status_code == 400
