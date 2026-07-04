from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any


def _load_json(path: str) -> dict[str, Any] | None:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return None
    return data


def _sha256(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_entry(path: str | None) -> dict[str, Any]:
    if not path:
        return {"path": None, "exists": False, "sha256": None}
    resolved = os.path.abspath(path)
    exists = os.path.exists(resolved)
    return {
        "path": resolved,
        "exists": exists,
        "sha256": _sha256(resolved) if exists else None,
    }


def build_bundle(
    *,
    report_path: str,
    output_manifest: str,
    output_summary: str,
    require_strict_dlq: bool = False,
) -> int:
    report = _load_json(report_path)
    if report is None:
        return 1

    smoke_path = report.get("smoke_result_path") if isinstance(report.get("smoke_result_path"), str) else None
    validator_log_path = report.get("validator_log_path") if isinstance(report.get("validator_log_path"), str) else None
    report_validator_log_path = (
        report.get("report_validator_log_path") if isinstance(report.get("report_validator_log_path"), str) else None
    )
    report_md_path = os.path.join(os.path.dirname(os.path.abspath(report_path)), "release_gate_wave2_report.md")
    dlq_preflight_path = (
        report.get("dlq_preflight_result_path") if isinstance(report.get("dlq_preflight_result_path"), str) else None
    )
    dlq_smoke_path = report.get("dlq_smoke_result_path") if isinstance(report.get("dlq_smoke_result_path"), str) else None

    artifacts = {
        "report_json": _file_entry(report_path),
        "report_md": _file_entry(report_md_path),
        "smoke_json": _file_entry(smoke_path),
        "smoke_validator_log": _file_entry(validator_log_path),
        "report_validator_log": _file_entry(report_validator_log_path),
    }

    if require_strict_dlq:
        artifacts["dlq_preflight_json"] = _file_entry(dlq_preflight_path)
        artifacts["dlq_smoke_json"] = _file_entry(dlq_smoke_path)

    missing = [name for name, meta in artifacts.items() if not meta.get("exists")]

    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "require_strict_dlq": require_strict_dlq,
        "decision": report.get("decision"),
        "overall_go": bool(report.get("overall_go")),
        "backend_url": report.get("backend_url"),
        "tenant_id": report.get("tenant_id"),
        "artifacts": artifacts,
        "missing_artifacts": missing,
        "bundle_ok": len(missing) == 0 and report.get("decision") == "GO" and bool(report.get("overall_go")),
    }

    with open(output_manifest, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)

    lines = [
        "# Wave 2 Release Evidence Bundle",
        "",
        f"- generated_at: {bundle['generated_at']}",
        f"- require_strict_dlq: {bundle['require_strict_dlq']}",
        f"- decision: {bundle['decision']}",
        f"- overall_go: {bundle['overall_go']}",
        f"- backend_url: {bundle['backend_url']}",
        f"- tenant_id: {bundle['tenant_id']}",
        f"- bundle_ok: {bundle['bundle_ok']}",
        "",
        "## Artifacts",
    ]
    for name, meta in artifacts.items():
        lines.append(f"- {name}: path={meta.get('path')}, exists={meta.get('exists')}, sha256={meta.get('sha256')}")

    if missing:
        lines.append("")
        lines.append("## Missing Artifacts")
        for item in missing:
            lines.append(f"- {item}")

    with open(output_summary, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return 0 if bundle["bundle_ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ALLinO Wave 2 release evidence bundle")
    parser.add_argument("--report", required=True, help="Path to release_gate_wave2_report.json")
    parser.add_argument("--output-manifest", required=True, help="Path for output evidence manifest JSON")
    parser.add_argument("--output-summary", required=True, help="Path for output evidence summary Markdown")
    parser.add_argument("--require-strict-dlq", action="store_true", help="Require strict DLQ artifacts in bundle")
    args = parser.parse_args()

    return build_bundle(
        report_path=args.report,
        output_manifest=args.output_manifest,
        output_summary=args.output_summary,
        require_strict_dlq=args.require_strict_dlq,
    )


if __name__ == "__main__":
    raise SystemExit(main())
