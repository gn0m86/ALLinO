from __future__ import annotations

import argparse
import json
import os
from typing import Any


def _safe_bool(value: Any) -> bool:
    return bool(value)


def _safe_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _load_json(path: str) -> dict[str, Any] | None:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        return None
    return payload


def validate_report(report: dict[str, Any], *, require_strict_dlq: bool = False) -> list[str]:
    errors: list[str] = []

    decision = report.get("decision")
    overall_go = _safe_bool(report.get("overall_go"))
    if decision != "GO":
        errors.append(f"decision must be GO, got {decision!r}")
    if not overall_go:
        errors.append("overall_go must be true")

    smoke_exit = _safe_int(report.get("smoke_exit_code"))
    validator_exit = _safe_int(report.get("validator_exit_code"))
    if smoke_exit != 0:
        errors.append(f"smoke_exit_code must be 0, got {smoke_exit!r}")
    if validator_exit != 0:
        errors.append(f"validator_exit_code must be 0, got {validator_exit!r}")

    smoke_path = report.get("smoke_result_path")
    validator_log_path = report.get("validator_log_path")
    if not isinstance(smoke_path, str) or not os.path.exists(smoke_path):
        errors.append("smoke_result_path is missing or file does not exist")
    if not isinstance(validator_log_path, str) or not os.path.exists(validator_log_path):
        errors.append("validator_log_path is missing or file does not exist")

    if require_strict_dlq:
        if not _safe_bool(report.get("require_external_worker")):
            errors.append("require_external_worker must be true in strict DLQ mode")
        if not _safe_bool(report.get("require_external_worker_dlq")):
            errors.append("require_external_worker_dlq must be true in strict DLQ mode")

        preflight_exit = _safe_int(report.get("dlq_preflight_exit_code"))
        dlq_exit = _safe_int(report.get("dlq_smoke_exit_code"))
        if preflight_exit != 0:
            errors.append(f"dlq_preflight_exit_code must be 0, got {preflight_exit!r}")
        if dlq_exit != 0:
            errors.append(f"dlq_smoke_exit_code must be 0, got {dlq_exit!r}")

        preflight_path = report.get("dlq_preflight_result_path")
        dlq_path = report.get("dlq_smoke_result_path")
        if not isinstance(preflight_path, str) or not os.path.exists(preflight_path):
            errors.append("dlq_preflight_result_path is missing or file does not exist")
        if not isinstance(dlq_path, str) or not os.path.exists(dlq_path):
            errors.append("dlq_smoke_result_path is missing or file does not exist")

        if isinstance(preflight_path, str) and os.path.exists(preflight_path):
            preflight_payload = _load_json(preflight_path)
            if not preflight_payload or not _safe_bool(preflight_payload.get("ok")):
                errors.append("dlq preflight artifact must contain ok=true")

        if isinstance(dlq_path, str) and os.path.exists(dlq_path):
            dlq_payload = _load_json(dlq_path)
            if not dlq_payload or not _safe_bool(dlq_payload.get("ok")):
                errors.append("dlq smoke artifact must contain ok=true")
            delta = dlq_payload.get("dlq_delta") if isinstance(dlq_payload, dict) else None
            if not isinstance(delta, int) or delta <= 0:
                errors.append("dlq smoke artifact must contain dlq_delta > 0")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ALLinO Wave 2 release gate report")
    parser.add_argument("--input", required=True, help="Path to release_gate_wave2_report.json")
    parser.add_argument(
        "--require-strict-dlq",
        action="store_true",
        help="Require strict DLQ fields and artifacts in release report",
    )
    args = parser.parse_args()

    report = _load_json(args.input)
    if report is None:
        print("NO-GO: release report path is invalid or JSON is not an object")
        return 1

    errors = validate_report(report, require_strict_dlq=args.require_strict_dlq)
    if errors:
        print("NO-GO: release gate report validation failed")
        for item in errors:
            print(f"- {item}")
        return 1

    print("GO: release gate report validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
