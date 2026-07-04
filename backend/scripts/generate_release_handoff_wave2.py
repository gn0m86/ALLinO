from __future__ import annotations

import argparse
import json
import os
from typing import Any


def _load_json(path: str) -> dict[str, Any] | None:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return None
    return data


def _line(name: str, value: Any) -> str:
    return f"- {name}: {value}"


def generate_handoff(*, report_path: str, bundle_path: str, output_path: str) -> int:
    report = _load_json(report_path)
    bundle = _load_json(bundle_path)
    if report is None or bundle is None:
        return 1

    decision = report.get("decision")
    overall_go = bool(report.get("overall_go"))
    bundle_ok = bool(bundle.get("bundle_ok"))

    lines = [
        "# Wave 2 Release Handoff",
        "",
        "## Summary",
        _line("decision", decision),
        _line("overall_go", overall_go),
        _line("bundle_ok", bundle_ok),
        _line("backend_url", report.get("backend_url")),
        _line("tenant_id", report.get("tenant_id")),
        _line("started_at", report.get("started_at")),
        _line("finished_at", report.get("finished_at")),
        "",
        "## Execution",
        _line("smoke_exit_code", report.get("smoke_exit_code")),
        _line("validator_exit_code", report.get("validator_exit_code")),
        _line("report_validator_exit_code", report.get("report_validator_exit_code")),
        _line("evidence_bundle_exit_code", report.get("evidence_bundle_exit_code")),
        _line("require_external_worker", report.get("require_external_worker")),
        _line("require_external_worker_dlq", report.get("require_external_worker_dlq")),
        _line("dlq_preflight_exit_code", report.get("dlq_preflight_exit_code")),
        _line("dlq_smoke_exit_code", report.get("dlq_smoke_exit_code")),
        "",
        "## Artifacts",
    ]

    artifacts: dict[str, Any] = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), dict) else {}
    for name, meta in artifacts.items():
        if isinstance(meta, dict):
            lines.append(
                f"- {name}: path={meta.get('path')}, exists={meta.get('exists')}, sha256={meta.get('sha256')}"
            )

    lines.extend([
        "",
        "## Missing Artifacts",
    ])

    missing = bundle.get("missing_artifacts") if isinstance(bundle.get("missing_artifacts"), list) else []
    if missing:
        for item in missing:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## Recommendation",
        f"- {('GO' if decision == 'GO' and overall_go and bundle_ok else 'NO-GO')}",
    ])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return 0 if decision == "GO" and overall_go and bundle_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ALLinO Wave 2 release handoff markdown")
    parser.add_argument("--report", required=True, help="Path to release_gate_wave2_report.json")
    parser.add_argument("--bundle", required=True, help="Path to release_gate_wave2_evidence_bundle.json")
    parser.add_argument("--output", required=True, help="Path to output handoff markdown")
    args = parser.parse_args()

    return generate_handoff(report_path=args.report, bundle_path=args.bundle, output_path=args.output)


if __name__ == "__main__":
    raise SystemExit(main())
