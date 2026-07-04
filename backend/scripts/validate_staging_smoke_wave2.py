from __future__ import annotations

import argparse
import json
import sys
from typing import Any

ALLOWED_CONNECTOR_STATUS = {"healthy", "degraded"}


def _safe_get(obj: dict[str, Any], *path: str) -> Any:
    current: Any = obj
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _is_check_ok(result: dict[str, Any], check_name: str) -> bool:
    return bool(_safe_get(result, "checks", check_name, "ok"))


def _validate_zoom_teams_processed_inserted(result: dict[str, Any], errors: list[str]) -> None:
    for source in ("zoom_sync", "teams_sync"):
        processed = _safe_get(result, "checks", source, "response", "processed")
        inserted = _safe_get(result, "checks", source, "response", "inserted")
        if not isinstance(processed, int) or processed <= 0:
            errors.append(f"{source}: expected processed > 0")
        if not isinstance(inserted, int) or inserted <= 0:
            errors.append(f"{source}: expected inserted > 0")


def _validate_connectors_registry(result: dict[str, Any], errors: list[str]) -> None:
    rows = _safe_get(result, "checks", "connectors_registry", "response")
    if not isinstance(rows, list):
        errors.append("connectors_registry: expected list response")
        return

    by_source = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("source_type"), str):
            by_source[row["source_type"]] = row

    for source in ("zoom", "teams"):
        row = by_source.get(source)
        if not row:
            errors.append(f"connectors_registry: missing source_type={source}")
            continue
        status = row.get("status")
        if status not in ALLOWED_CONNECTOR_STATUS:
            errors.append(
                f"connectors_registry: source_type={source} has status={status!r}, expected one of {sorted(ALLOWED_CONNECTOR_STATUS)}"
            )


def _validate_audit_actions(result: dict[str, Any], errors: list[str]) -> None:
    rows = _safe_get(result, "checks", "audit", "response")
    if not isinstance(rows, list):
        errors.append("audit: expected list response")
        return

    actions = {row.get("action") for row in rows if isinstance(row, dict)}

    required = {
        "connector.zoom.sync.batch",
        "connector.teams.sync.batch",
    }

    for action in required:
        if action not in actions:
            errors.append(f"audit: missing action {action}")


def _validate_external_worker_mode(result: dict[str, Any], errors: list[str]) -> None:
    for source in ("zoom_sync", "teams_sync"):
        mode = _safe_get(result, "checks", source, "response", "event_bus")
        if mode != "external_worker":
            errors.append(f"{source}: expected event_bus=external_worker, got {mode!r}")


def validate_result(result: dict[str, Any], *, require_external_worker: bool = False) -> list[str]:
    errors: list[str] = []

    for check in ("health", "zoom_sync", "teams_sync", "connectors_registry", "audit", "stats"):
        if not _is_check_ok(result, check):
            errors.append(f"check failed: {check}")

    script_errors = result.get("errors")
    if isinstance(script_errors, list) and script_errors:
        errors.append(f"script reported errors: {len(script_errors)} item(s)")

    _validate_zoom_teams_processed_inserted(result, errors)
    _validate_connectors_registry(result, errors)
    _validate_audit_actions(result, errors)
    if require_external_worker:
        _validate_external_worker_mode(result, errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ALLinO Wave 2 staging smoke result")
    parser.add_argument("--input", required=True, help="Path to staging_smoke_wave2_result.json")
    parser.add_argument(
        "--require-external-worker",
        action="store_true",
        help="Require event_bus=external_worker in zoom/teams sync responses",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        print("NO-GO: input JSON must be an object")
        return 1

    errors = validate_result(payload, require_external_worker=args.require_external_worker)
    if errors:
        print("NO-GO: staging smoke evidence validation failed")
        for item in errors:
            print(f"- {item}")
        return 1

    print("GO: staging smoke evidence validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
