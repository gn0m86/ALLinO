from __future__ import annotations

import argparse
import json
import os
from typing import Any

import redis


REQUIRED_ENV_VARS = (
    "ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX",
    "ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED",
    "ALLINO_EVENT_BUS_ENABLED",
)


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def run_preflight(*, redis_url: str, output_path: str) -> int:
    checks: dict[str, Any] = {}
    errors: list[str] = []

    env_snapshot = {name: os.getenv(name) for name in REQUIRED_ENV_VARS}
    missing_or_invalid = []

    force_prefix = env_snapshot["ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX"]
    if not force_prefix:
        missing_or_invalid.append("ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX")
    elif not force_prefix.startswith("connector."):
        errors.append(
            "ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX must start with 'connector.'"
        )

    if not _is_truthy(env_snapshot["ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED"]):
        missing_or_invalid.append("ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED=true")

    if not _is_truthy(env_snapshot["ALLINO_EVENT_BUS_ENABLED"]):
        missing_or_invalid.append("ALLINO_EVENT_BUS_ENABLED=true")

    if missing_or_invalid:
        errors.append("Missing/invalid env requirements: " + ", ".join(missing_or_invalid))

    checks["env"] = {
        "ok": len(missing_or_invalid) == 0 and not any("must start" in e for e in errors),
        "values": env_snapshot,
    }

    redis_ok = False
    redis_error = None
    try:
        client = redis.from_url(redis_url, decode_responses=True)
        redis_ok = bool(client.ping())
        if not redis_ok:
            redis_error = "Redis ping returned false"
    except Exception as exc:  # pragma: no cover
        redis_error = str(exc)

    if not redis_ok:
        errors.append(f"Redis is not reachable: {redis_error or 'unknown error'}")

    checks["redis"] = {
        "ok": redis_ok,
        "url": redis_url,
        "error": redis_error,
    }

    result = {
        "ok": len(errors) == 0,
        "checks": checks,
        "errors": errors,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return 0 if result["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="ALLinO strict DLQ preflight")
    parser.add_argument("--redis-url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    return run_preflight(redis_url=args.redis_url, output_path=args.output)


if __name__ == "__main__":
    raise SystemExit(main())
