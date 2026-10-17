from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from collections import defaultdict
from typing import Any

from ..core.config import (
    ALLINO_EVENT_BUS_EXTERNAL_WORKER_BACKOFF_SECONDS,
    ALLINO_EVENT_BUS_EXTERNAL_WORKER_DLQ_STREAM,
    ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX,
    ALLINO_EVENT_BUS_EXTERNAL_WORKER_MAX_ATTEMPTS,
    ALLINO_REDIS_STREAM_PREFIX,
    ALLINO_REDIS_URL,
)
from ..services.ingestion_processor import process_connector_batch

logger = logging.getLogger(__name__)

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None


def _decode(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def check_worker_health() -> tuple[bool, str]:
    if redis is None:
        return False, "redis package is not installed"
    try:
        client = redis.from_url(ALLINO_REDIS_URL, decode_responses=False)
        pong = client.ping()
        if pong:
            return True, "ok"
        return False, "redis ping returned false"
    except Exception as exc:
        return False, f"redis connectivity failed: {exc}"


def _write_result(client: Any, batch_id: str, payload: dict[str, Any]) -> None:
    result_key = f"{ALLINO_REDIS_STREAM_PREFIX}:results:{batch_id}"
    client.setex(result_key, 120, json.dumps(payload, ensure_ascii=True))


def _push_dlq(client: Any, *, batch_id: str, batch: dict[str, Any], error: str, attempts: int) -> None:
    events = batch.get("events", {})
    batch_size = int(batch.get("batch_size", 0))
    ordered = [events.get(i, {}) for i in range(batch_size)]
    client.xadd(
        ALLINO_EVENT_BUS_EXTERNAL_WORKER_DLQ_STREAM,
        {
            "batch_id": batch_id,
            "tenant_id": str(batch.get("tenant_id", "")),
            "source": str(batch.get("source", "")),
            "action_prefix": str(batch.get("action_prefix", "")),
            "attempts": str(attempts),
            "error": error,
            "events": json.dumps(ordered, ensure_ascii=True),
        },
    )


def process_completed_batch(
    *,
    client: Any,
    batch_id: str,
    batch: dict[str, Any],
) -> None:
    events = batch.get("events", {})
    batch_size = int(batch.get("batch_size", 0))
    ordered = [events.get(i, {}) for i in range(batch_size)]

    attempts = 0
    last_error: str | None = None
    for attempts in range(1, max(1, ALLINO_EVENT_BUS_EXTERNAL_WORKER_MAX_ATTEMPTS) + 1):
        try:
            if ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX and str(
                batch.get("action_prefix", "")
            ).startswith(ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX):
                raise RuntimeError("forced external worker error for DLQ smoke")

            counts = process_connector_batch(
                events=ordered,
                tenant_id=batch["tenant_id"],
                action_prefix=batch["action_prefix"],
            )
            _write_result(client, batch_id, {**counts, "attempts": attempts, "error": None})
            return
        except Exception as exc:  # pragma: no cover - resilience path
            last_error = str(exc)
            if attempts < ALLINO_EVENT_BUS_EXTERNAL_WORKER_MAX_ATTEMPTS:
                time.sleep(max(0.0, ALLINO_EVENT_BUS_EXTERNAL_WORKER_BACKOFF_SECONDS))

    assert last_error is not None
    _push_dlq(client, batch_id=batch_id, batch=batch, error=last_error, attempts=attempts)
    _write_result(
        client,
        batch_id,
        {
            "processed": 0,
            "inserted": 0,
            "duplicates": 0,
            "rejected": batch_size,
            "total_lag_ms": 0.0,
            "lag_samples": 0,
            "attempts": attempts,
            "error": last_error,
        },
    )


def run_worker_loop(poll_interval_seconds: float = 0.25) -> None:
    if redis is None:
        raise RuntimeError("redis package is required for event bus worker")

    client = redis.from_url(ALLINO_REDIS_URL, decode_responses=False)
    request_stream = f"{ALLINO_REDIS_STREAM_PREFIX}:requests"
    last_id = "$"

    batches: dict[str, dict[str, Any]] = defaultdict(dict)

    logger.info("Starting event bus worker on stream %s", request_stream)
    while True:
        entries = client.xread({request_stream: last_id}, block=1000, count=100)
        if not entries:
            time.sleep(poll_interval_seconds)
            continue

        for _, stream_entries in entries:
            for entry_id, fields in stream_entries:
                last_id = _decode(entry_id)

                batch_id = _decode(fields.get(b"batch_id", b""))
                tenant_id = _decode(fields.get(b"tenant_id", b""))
                source = _decode(fields.get(b"source", b""))
                action_prefix = _decode(fields.get(b"action_prefix", b""))
                event_index = int(_decode(fields.get(b"event_index", b"0")))
                batch_size = int(_decode(fields.get(b"batch_size", b"0")))
                raw_event = _decode(fields.get(b"raw_event", b"{}"))

                if not batch_id or batch_size <= 0:
                    continue

                batch = batches.setdefault(
                    batch_id,
                    {
                        "tenant_id": tenant_id,
                        "source": source,
                        "action_prefix": action_prefix,
                        "batch_size": batch_size,
                        "events": {},
                    },
                )

                try:
                    payload = json.loads(raw_event)
                except json.JSONDecodeError:
                    payload = {}
                if isinstance(payload, dict):
                    batch["events"][event_index] = payload

                if len(batch["events"]) < batch["batch_size"]:
                    continue

                process_completed_batch(client=client, batch_id=batch_id, batch=batch)
                batches.pop(batch_id, None)


def main() -> None:
    parser = argparse.ArgumentParser(description="ALLinO external event bus worker")
    parser.add_argument("--healthcheck", action="store_true", help="Check Redis connectivity and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.healthcheck:
        ok, message = check_worker_health()
        if ok:
            print("ok")
            return
        raise RuntimeError(message)

    # Docker runs this as PID 1, where SIGTERM is ignored unless a handler is
    # installed -- without one, `docker stop` waits 10s and then SIGKILLs it.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    run_worker_loop()


if __name__ == "__main__":
    main()
