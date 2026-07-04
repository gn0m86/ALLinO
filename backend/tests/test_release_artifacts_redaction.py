import importlib.util
import json
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "redact_release_artifacts.py"
    spec = importlib.util.spec_from_file_location("redact_release_artifacts", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


redactor = _load_module()


def _write(path: Path, content: str) -> str:
    path.write_text(content, encoding="utf-8")
    return str(path)


def _write_json(path: Path, payload: dict) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_redact_artifacts_success(tmp_path: Path) -> None:
    smoke = _write(tmp_path / "smoke.json", '{"token":"abc123"}')
    validator_log = _write(tmp_path / "validator.log", "X-API-Key: super-secret")
    report_validator_log = _write(tmp_path / "report_validator.log", "Authorization: Bearer xyz")
    bundle_md = _write(tmp_path / "bundle.md", "api_key=secret")
    handoff_md = _write(tmp_path / "handoff.md", "password=123456")

    report = {
        "smoke_result_path": smoke,
        "validator_log_path": validator_log,
        "report_validator_log_path": report_validator_log,
        "evidence_bundle_md_path": bundle_md,
        "release_handoff_md_path": handoff_md,
    }
    report_path = _write_json(tmp_path / "release_gate_wave2_report.json", report)
    _write(tmp_path / "release_gate_wave2_report.md", "token: report-token")

    out_dir = tmp_path / "sanitized"
    manifest_path = tmp_path / "manifest.json"

    code = redactor.redact_artifacts(
        report_path=report_path,
        output_dir=str(out_dir),
        output_manifest=str(manifest_path),
    )

    assert code == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["ok"] is True
    assert manifest["total_replacements"] > 0

    sanitized_validator = (out_dir / "validator.log").read_text(encoding="utf-8")
    assert "super-secret" not in sanitized_validator
    assert "[REDACTED]" in sanitized_validator


def test_redact_artifacts_missing_file_fails(tmp_path: Path) -> None:
    report = {
        "smoke_result_path": str(tmp_path / "missing.json"),
        "validator_log_path": str(tmp_path / "missing.log"),
    }
    report_path = _write_json(tmp_path / "release_gate_wave2_report.json", report)

    out_dir = tmp_path / "sanitized"
    manifest_path = tmp_path / "manifest_missing.json"

    code = redactor.redact_artifacts(
        report_path=report_path,
        output_dir=str(out_dir),
        output_manifest=str(manifest_path),
    )

    assert code == 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["ok"] is False
    assert any(item["error"] == "missing" for item in manifest["files"])
