import importlib.util
import json
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "generate_release_handoff_wave2.py"
    spec = importlib.util.spec_from_file_location("generate_release_handoff_wave2", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


handoff = _load_module()


def _write_json(path: Path, payload: dict) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_generate_handoff_success(tmp_path: Path) -> None:
    report_path = _write_json(
        tmp_path / "report.json",
        {
            "decision": "GO",
            "overall_go": True,
            "backend_url": "http://localhost:8000",
            "tenant_id": "tenant_demo",
            "started_at": "2026-07-01T00:00:00Z",
            "finished_at": "2026-07-01T00:10:00Z",
            "smoke_exit_code": 0,
            "validator_exit_code": 0,
            "report_validator_exit_code": 0,
            "evidence_bundle_exit_code": 0,
            "require_external_worker": True,
            "require_external_worker_dlq": True,
            "dlq_preflight_exit_code": 0,
            "dlq_smoke_exit_code": 0,
        },
    )
    bundle_path = _write_json(
        tmp_path / "bundle.json",
        {
            "bundle_ok": True,
            "artifacts": {
                "report_json": {"path": "a", "exists": True, "sha256": "x"},
                "report_md": {"path": "b", "exists": True, "sha256": "y"},
            },
            "missing_artifacts": [],
        },
    )

    output = tmp_path / "handoff.md"
    code = handoff.generate_handoff(report_path=report_path, bundle_path=bundle_path, output_path=str(output))
    assert code == 0
    text = output.read_text(encoding="utf-8")
    assert "# Wave 2 Release Handoff" in text
    assert "- GO" in text


def test_generate_handoff_no_go(tmp_path: Path) -> None:
    report_path = _write_json(tmp_path / "report_bad.json", {"decision": "NO-GO", "overall_go": False})
    bundle_path = _write_json(tmp_path / "bundle_bad.json", {"bundle_ok": False, "artifacts": {}, "missing_artifacts": ["x"]})

    output = tmp_path / "handoff_bad.md"
    code = handoff.generate_handoff(report_path=report_path, bundle_path=bundle_path, output_path=str(output))
    assert code == 1
    text = output.read_text(encoding="utf-8")
    assert "NO-GO" in text
