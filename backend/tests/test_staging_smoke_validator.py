from pathlib import Path
import importlib.util


def _load_validator_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "validate_staging_smoke_wave2.py"
    spec = importlib.util.spec_from_file_location("validate_staging_smoke_wave2", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_validator_module()


def _valid_result() -> dict:
    return {
        "checks": {
            "health": {"ok": True, "response": {"status": "ok"}},
            "zoom_sync": {
                "ok": True,
                "response": {"processed": 1, "inserted": 1, "health": "healthy", "event_bus": "external_worker"},
            },
            "teams_sync": {
                "ok": True,
                "response": {"processed": 1, "inserted": 1, "health": "healthy", "event_bus": "external_worker"},
            },
            "connectors_registry": {
                "ok": True,
                "response": [
                    {"source_type": "zoom", "status": "healthy"},
                    {"source_type": "teams", "status": "degraded"},
                ],
            },
            "audit": {
                "ok": True,
                "response": [
                    {"action": "connector.zoom.sync.batch"},
                    {"action": "connector.teams.sync.batch"},
                ],
            },
            "stats": {"ok": True, "response": {"inbox_count": 2, "audit_count": 4}},
        },
        "errors": [],
    }


def test_validate_result_success() -> None:
    errors = validator.validate_result(_valid_result())
    assert errors == []


def test_validate_result_detects_missing_audit_action() -> None:
    payload = _valid_result()
    payload["checks"]["audit"]["response"] = [{"action": "connector.zoom.sync.batch"}]

    errors = validator.validate_result(payload)

    assert any("connector.teams.sync.batch" in item for item in errors)


def test_validate_result_detects_bad_connector_status() -> None:
    payload = _valid_result()
    payload["checks"]["connectors_registry"]["response"][1]["status"] = "error"

    errors = validator.validate_result(payload)

    assert any("source_type=teams" in item for item in errors)


def test_validate_result_detects_failed_check_flag() -> None:
    payload = _valid_result()
    payload["checks"]["teams_sync"]["ok"] = False

    errors = validator.validate_result(payload)

    assert any("check failed: teams_sync" == item for item in errors)


def test_validate_result_external_worker_required_success() -> None:
    errors = validator.validate_result(_valid_result(), require_external_worker=True)
    assert errors == []


def test_validate_result_external_worker_required_failure() -> None:
    payload = _valid_result()
    payload["checks"]["teams_sync"]["response"]["event_bus"] = "redis_fallback"

    errors = validator.validate_result(payload, require_external_worker=True)
    assert any("teams_sync: expected event_bus=external_worker" in item for item in errors)
