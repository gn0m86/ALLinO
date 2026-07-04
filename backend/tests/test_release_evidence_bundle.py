import importlib.util
import json
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build_release_evidence_bundle.py"
    spec = importlib.util.spec_from_file_location("build_release_evidence_bundle", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bundle = _load_module()


def _write_json(path: Path, payload: dict) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_build_bundle_success_non_strict(tmp_path: Path) -> None:
    smoke = _write_json(tmp_path / "staging_smoke_wave2_result.json", {"checks": {}, "errors": []})
    (tmp_path / "staging_smoke_validator.log").write_text("GO", encoding="utf-8")
    (tmp_path / "release_gate_wave2_report_validator.log").write_text("GO", encoding="utf-8")
    (tmp_path / "release_gate_wave2_report.md").write_text("# report", encoding="utf-8")

    report = {
        "decision": "GO",
        "overall_go": True,
        "backend_url": "http://localhost:8000",
        "tenant_id": "tenant_demo",
        "smoke_result_path": smoke,
        "validator_log_path": str(tmp_path / "staging_smoke_validator.log"),
        "report_validator_log_path": str(tmp_path / "release_gate_wave2_report_validator.log"),
    }
    report_path = _write_json(tmp_path / "release_gate_wave2_report.json", report)

    manifest = tmp_path / "bundle.json"
    summary = tmp_path / "bundle.md"
    code = bundle.build_bundle(
        report_path=report_path,
        output_manifest=str(manifest),
        output_summary=str(summary),
        require_strict_dlq=False,
    )

    assert code == 0
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["bundle_ok"] is True
    assert payload["missing_artifacts"] == []


def test_build_bundle_fails_when_strict_missing_artifacts(tmp_path: Path) -> None:
    smoke = _write_json(tmp_path / "staging_smoke_wave2_result.json", {"checks": {}, "errors": []})
    (tmp_path / "staging_smoke_validator.log").write_text("GO", encoding="utf-8")
    (tmp_path / "release_gate_wave2_report_validator.log").write_text("GO", encoding="utf-8")
    (tmp_path / "release_gate_wave2_report.md").write_text("# report", encoding="utf-8")

    report = {
        "decision": "GO",
        "overall_go": True,
        "backend_url": "http://localhost:8000",
        "tenant_id": "tenant_demo",
        "smoke_result_path": smoke,
        "validator_log_path": str(tmp_path / "staging_smoke_validator.log"),
        "report_validator_log_path": str(tmp_path / "release_gate_wave2_report_validator.log"),
        "dlq_preflight_result_path": str(tmp_path / "missing_preflight.json"),
        "dlq_smoke_result_path": str(tmp_path / "missing_dlq.json"),
    }
    report_path = _write_json(tmp_path / "release_gate_wave2_report.json", report)

    manifest = tmp_path / "bundle_strict.json"
    summary = tmp_path / "bundle_strict.md"
    code = bundle.build_bundle(
        report_path=report_path,
        output_manifest=str(manifest),
        output_summary=str(summary),
        require_strict_dlq=True,
    )

    assert code == 1
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["bundle_ok"] is False
    assert "dlq_preflight_json" in payload["missing_artifacts"]
    assert "dlq_smoke_json" in payload["missing_artifacts"]
