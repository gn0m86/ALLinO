from fastapi.testclient import TestClient

from app.db import session
from app.main import app
from app.services.metrics import MetricsStore, get_metrics_store


# ---------------------------------------------------------------------------
# Pure unit tests — MetricsStore accumulation, without HTTP
# ---------------------------------------------------------------------------


def test_record_sync_accumulates_counts() -> None:
    store = MetricsStore()
    store.record_sync(
        tenant_id="tenant_a",
        source="test_source",
        processed=3,
        inserted=2,
        duplicates=1,
        rejected=0,
        total_lag_ms=3000.0,
        lag_samples=3,
        health="healthy",
    )
    store.record_sync(
        tenant_id="tenant_a",
        source="test_source",
        processed=2,
        inserted=1,
        duplicates=0,
        rejected=1,
        total_lag_ms=1000.0,
        lag_samples=1,
        health="degraded",
    )

    snapshot = store.snapshot("tenant_a")
    m = snapshot["test_source"]
    assert m["sync_count"] == 2
    assert m["processed"] == 5
    assert m["inserted"] == 3
    assert m["duplicates"] == 1
    assert m["rejected"] == 1
    assert m["avg_lag_ms"] == 1000.0  # (3000 + 1000) / 4 samples
    assert m["last_health"] == "degraded"


def test_record_sync_tracks_retry_count() -> None:
    store = MetricsStore()
    store.record_sync(
        tenant_id="tenant_a",
        source="src",
        processed=1,
        inserted=1,
        duplicates=0,
        rejected=0,
        total_lag_ms=0.0,
        lag_samples=1,
        health="healthy",
        retry_count=2,
    )
    snapshot = store.snapshot("tenant_a")
    assert snapshot["src"]["retry_count"] == 2


def test_snapshot_keeps_sources_independent() -> None:
    store = MetricsStore()
    store.record_sync(
        tenant_id="tenant_a",
        source="github",
        processed=1,
        inserted=1,
        duplicates=0,
        rejected=0,
        total_lag_ms=100.0,
        lag_samples=1,
        health="healthy",
    )
    store.record_sync(
        tenant_id="tenant_a",
        source="gitlab",
        processed=1,
        inserted=0,
        duplicates=1,
        rejected=0,
        total_lag_ms=200.0,
        lag_samples=1,
        health="healthy",
    )
    snapshot = store.snapshot("tenant_a")
    assert set(snapshot.keys()) == {"github", "gitlab"}
    assert snapshot["github"]["inserted"] == 1
    assert snapshot["gitlab"]["duplicates"] == 1


def test_snapshot_avg_lag_zero_when_no_samples() -> None:
    store = MetricsStore()
    store.record_sync(
        tenant_id="tenant_a",
        source="all_rejected",
        processed=2,
        inserted=0,
        duplicates=0,
        rejected=2,
        total_lag_ms=0.0,
        lag_samples=0,
        health="degraded",
    )
    snapshot = store.snapshot("tenant_a")
    assert snapshot["all_rejected"]["avg_lag_ms"] == 0.0


def test_snapshot_is_tenant_scoped() -> None:
    store = MetricsStore()
    store.record_sync(
        tenant_id="tenant_a",
        source="github",
        processed=1,
        inserted=1,
        duplicates=0,
        rejected=0,
        total_lag_ms=10.0,
        lag_samples=1,
        health="healthy",
    )
    store.record_sync(
        tenant_id="tenant_b",
        source="github",
        processed=2,
        inserted=2,
        duplicates=0,
        rejected=0,
        total_lag_ms=20.0,
        lag_samples=2,
        health="healthy",
    )

    snapshot_a = store.snapshot("tenant_a")
    snapshot_b = store.snapshot("tenant_b")
    assert snapshot_a["github"]["processed"] == 1
    assert snapshot_b["github"]["processed"] == 2


# ---------------------------------------------------------------------------
# API-level: connector sync feeds the shared metrics store, /metrics exposes it
# ---------------------------------------------------------------------------


def test_metrics_endpoint_reflects_connector_sync(tmp_path) -> None:
    session.DB_PATH = tmp_path / "metrics_api.db"

    notification = {
        "id": "gh-metrics-1",
        "updated_at": "2026-06-30T10:00:00Z",
        "reason": "mention",
        "subject": {"title": "Metrics test issue", "type": "Issue"},
        "repository": {"full_name": "org/repo"},
    }

    with TestClient(app) as client:
        sync_resp = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo",
            json={"seeded_notifications": [notification]},
        )
        assert sync_resp.status_code == 200

        metrics_resp = client.get("/api/v1/ingestion/metrics?tenant_id=tenant_demo")
        assert metrics_resp.status_code == 200

    snapshot = get_metrics_store().snapshot("tenant_demo")
    assert "github" in snapshot
    github_metrics = snapshot["github"]
    assert github_metrics["processed"] >= 1
    assert github_metrics["inserted"] >= 1
    assert github_metrics["last_health"] == "healthy"
    assert github_metrics["avg_lag_ms"] >= 0.0


def test_metrics_endpoint_is_tenant_scoped(tmp_path) -> None:
    session.DB_PATH = tmp_path / "metrics_tenant_scope.db"

    notification_a = {
        "id": "gh-metrics-a",
        "updated_at": "2026-06-30T10:00:00Z",
        "reason": "mention",
        "subject": {"title": "Tenant A", "type": "Issue"},
        "repository": {"full_name": "org/repo-a"},
    }
    notification_b = {
        "id": "gh-metrics-b",
        "updated_at": "2026-06-30T10:00:00Z",
        "reason": "mention",
        "subject": {"title": "Tenant B", "type": "Issue"},
        "repository": {"full_name": "org/repo-b"},
    }

    with TestClient(app) as client:
        r1 = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_a",
            json={"seeded_notifications": [notification_a]},
        )
        assert r1.status_code == 200

        r2 = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_b",
            json={"seeded_notifications": [notification_b]},
        )
        assert r2.status_code == 200

        m_a = client.get("/api/v1/ingestion/metrics?tenant_id=tenant_a")
        m_b = client.get("/api/v1/ingestion/metrics?tenant_id=tenant_b")
        assert m_a.status_code == 200
        assert m_b.status_code == 200

    metrics_a = m_a.json()
    metrics_b = m_b.json()
    assert metrics_a["github"]["processed"] >= 1
    assert metrics_b["github"]["processed"] >= 1
