import importlib.util
from pathlib import Path


def _load_validator_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "validate_release_gate_wave2_report.py"
    spec = importlib.util.spec_from_file_location("validate_release_gate_wave2_report", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_validator_module()


def _write_json(path: Path, payload: dict) -> str:
    import json

    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_validate_report_success_non_strict(tmp_path: Path) -> None:
    smoke_path = _write_json(tmp_path / "smoke.json", {"checks": {}, "errors": []})
    log_path = str(tmp_path / "validator.log")
    Path(log_path).write_text("GO", encoding="utf-8")

    report = {
        "decision": "GO",
        "overall_go": True,
        "smoke_exit_code": 0,
        "validator_exit_code": 0,
        "smoke_result_path": smoke_path,
        "validator_log_path": log_path,
        "require_external_worker": False,
        "require_external_worker_dlq": False,
    }

    errors = validator.validate_report(report, require_strict_dlq=False)
    assert errors == []


def test_validate_report_success_strict_dlq(tmp_path: Path) -> None:
    smoke_path = _write_json(tmp_path / "smoke.json", {"checks": {}, "errors": []})
    log_path = str(tmp_path / "validator.log")
    Path(log_path).write_text("GO", encoding="utf-8")

    preflight_path = _write_json(tmp_path / "preflight.json", {"ok": True, "checks": {}, "errors": []})
    dlq_path = _write_json(
        tmp_path / "dlq.json",
        {"ok": True, "dlq_delta": 1, "event_bus": "redis_fallback", "observed_reason": "external_worker_error_result"},
    )

    report = {
        "decision": "GO",
        "overall_go": True,
        "smoke_exit_code": 0,
        "validator_exit_code": 0,
        "smoke_result_path": smoke_path,
        "validator_log_path": log_path,
        "require_external_worker": True,
        "require_external_worker_dlq": True,
        "dlq_preflight_exit_code": 0,
        "dlq_smoke_exit_code": 0,
        "dlq_preflight_result_path": preflight_path,
        "dlq_smoke_result_path": dlq_path,
    }

    errors = validator.validate_report(report, require_strict_dlq=True)
    assert errors == []


def test_validate_report_fails_strict_dlq_missing_artifacts(tmp_path: Path) -> None:
    smoke_path = _write_json(tmp_path / "smoke.json", {"checks": {}, "errors": []})
    log_path = str(tmp_path / "validator.log")
    Path(log_path).write_text("GO", encoding="utf-8")

    report = {
        "decision": "GO",
        "overall_go": True,
        "smoke_exit_code": 0,
        "validator_exit_code": 0,
        "smoke_result_path": smoke_path,
        "validator_log_path": log_path,
        "require_external_worker": True,
        "require_external_worker_dlq": True,
        "dlq_preflight_exit_code": 1,
        "dlq_smoke_exit_code": 1,
        "dlq_preflight_result_path": str(tmp_path / "missing_preflight.json"),
        "dlq_smoke_result_path": str(tmp_path / "missing_dlq.json"),
    }

    errors = validator.validate_report(report, require_strict_dlq=True)
    assert any("dlq_preflight_exit_code" in item for item in errors)
    assert any("dlq_smoke_exit_code" in item for item in errors)
    assert any("dlq_preflight_result_path" in item for item in errors)
    assert any("dlq_smoke_result_path" in item for item in errors)
