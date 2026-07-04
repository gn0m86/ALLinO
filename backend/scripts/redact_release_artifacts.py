from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


REPLACEMENT = "[REDACTED]"

PATTERNS = (
    re.compile(r"(?i)(x-api-key\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)([^\s,;]+)"),
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._~+\-/=]+)"),
    re.compile(r"(?i)(\bapi[_-]?key\b\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(\btoken\b\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(\bsecret\b\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(\bpassword\b\s*[:=]\s*)([^\s,;]+)"),
)


def _load_json(path: str) -> dict[str, Any] | None:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return None
    return data


def _read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return Path(path).read_text(encoding="latin-1")


def _redact_text(text: str) -> tuple[str, int]:
    total = 0
    current = text
    for pattern in PATTERNS:
        current, count = pattern.subn(lambda m: f"{m.group(1)}{REPLACEMENT}", current)
        total += count
    return current, total


def _collect_paths(report: dict[str, Any]) -> list[str]:
    keys = [
        "smoke_result_path",
        "validator_log_path",
        "report_validator_log_path",
        "evidence_bundle_log_path",
        "evidence_bundle_json_path",
        "evidence_bundle_md_path",
        "release_handoff_log_path",
        "release_handoff_md_path",
        "dlq_preflight_result_path",
        "dlq_smoke_result_path",
    ]

    paths: list[str] = []
    for key in keys:
        value = report.get(key)
        if isinstance(value, str) and value.strip():
            paths.append(value)

    report_path = report.get("_report_path")
    if isinstance(report_path, str) and report_path.strip():
        report_dir = os.path.dirname(os.path.abspath(report_path))
        paths.append(os.path.join(report_dir, "release_gate_wave2_report.md"))

    unique_paths: list[str] = []
    seen: set[str] = set()
    for p in paths:
        abs_p = os.path.abspath(p)
        if abs_p not in seen:
            seen.add(abs_p)
            unique_paths.append(abs_p)
    return unique_paths


def redact_artifacts(*, report_path: str, output_dir: str, output_manifest: str) -> int:
    report = _load_json(report_path)
    if report is None:
        return 1

    report["_report_path"] = os.path.abspath(report_path)

    os.makedirs(output_dir, exist_ok=True)

    files = _collect_paths(report)
    entries: list[dict[str, Any]] = []
    failures = 0

    for src in files:
        if not os.path.exists(src):
            entries.append(
                {
                    "source": src,
                    "sanitized": None,
                    "exists": False,
                    "replacements": 0,
                    "error": "missing",
                }
            )
            failures += 1
            continue

        try:
            content = _read_text(src)
            redacted, replaced = _redact_text(content)
            dst = os.path.join(output_dir, os.path.basename(src))
            Path(dst).write_text(redacted, encoding="utf-8")
            entries.append(
                {
                    "source": src,
                    "sanitized": os.path.abspath(dst),
                    "exists": True,
                    "replacements": replaced,
                    "error": None,
                }
            )
        except Exception as exc:  # pragma: no cover
            entries.append(
                {
                    "source": src,
                    "sanitized": None,
                    "exists": True,
                    "replacements": 0,
                    "error": str(exc),
                }
            )
            failures += 1

    manifest = {
        "report_path": os.path.abspath(report_path),
        "sanitized_output_dir": os.path.abspath(output_dir),
        "files": entries,
        "total_files": len(entries),
        "total_replacements": sum(int(item.get("replacements", 0)) for item in entries),
        "ok": failures == 0,
    }

    with open(output_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return 0 if manifest["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Redact ALLinO release artifacts")
    parser.add_argument("--report", required=True, help="Path to release_gate_wave2_report.json")
    parser.add_argument("--output-dir", required=True, help="Directory for sanitized files")
    parser.add_argument("--output-manifest", required=True, help="Path for redaction manifest json")
    args = parser.parse_args()

    return redact_artifacts(report_path=args.report, output_dir=args.output_dir, output_manifest=args.output_manifest)


if __name__ == "__main__":
    raise SystemExit(main())
