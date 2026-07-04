from __future__ import annotations

import json
import logging
from queue import Empty, Queue
from threading import Event, Lock, Thread
from time import sleep, time
from typing import Any, Callable
from uuid import uuid4

from ..core.config import (
    ALLINO_EVENT_BUS_ASYNC_MAX_ATTEMPTS,
    ALLINO_EVENT_BUS_ASYNC_CONSUMER_ENABLED,
    ALLINO_EVENT_BUS_ASYNC_TIMEOUT_SECONDS,
    ALLINO_EVENT_BUS_ENABLED,
    ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED,
    ALLINO_EVENT_BUS_EXTERNAL_WORKER_TIMEOUT_SECONDS,
    ALLINO_REDIS_STREAM_PREFIX,
    ALLINO_REDIS_URL,
)

logger = logging.getLogger(__name__)

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - optional dependency path
    redis = None


class EventBusMode:
    DIRECT = "direct"
    WORKER_ASYNC = "worker_async"
    EXTERNAL_WORKER = "external_worker"
    REDIS_STREAM = "redis_stream"
    REDIS_FALLBACK = "redis_fallback"


_JOB_QUEUE: Queue[dict[str, Any]] = Queue()
_JOB_RESULTS: dict[str, dict[str, Any]] = {}
_RESULT_LOCK = Lock()
_WORKER_STARTED = False


def _worker_loop() -> None:
    while True:
        try:
            job = _JOB_QUEUE.get(timeout=0.5)
        except Empty:
            continue

        result = {
            "counts": {
                "processed": 0,
                "inserted": 0,
                "duplicates": 0,
                "rejected": 0,
                "total_lag_ms": 0.0,
                "lag_samples": 0,
            },
            "error": None,
            "attempts": 0,
        }
        max_attempts = max(1, int(job.get("max_attempts", 1)))
        for attempt in range(1, max_attempts + 1):
            result["attempts"] = attempt
            try:
                counts = job["processor"](job["events"], job["tenant_id"], job["action_prefix"])
                result["counts"] = counts
                result["error"] = None
                break
            except Exception as exc:  # pragma: no cover - resilience path
                result["error"] = str(exc)
                if attempt >= max_attempts:
                    logger.exception("Event-bus worker exhausted retries: %s", exc)

        with _RESULT_LOCK:
            _JOB_RESULTS[job["id"]] = result
        job["done"].set()


def _ensure_worker_started() -> None:
    global _WORKER_STARTED
    if _WORKER_STARTED:
        return
    thread = Thread(target=_worker_loop, name="allino-event-bus-worker", daemon=True)
    thread.start()
    _WORKER_STARTED = True


def _process_with_async_worker(
    *,
    tenant_id: str,
    source: str,
    action_prefix: str,
    events: list[dict[str, Any]],
    processor: Callable[[list[dict[str, Any]], str, str], dict[str, int | float]],
) -> tuple[dict[str, int | float], dict[str, Any]]:
    _ensure_worker_started()
    job_id = str(uuid4())
    done = Event()

    _JOB_QUEUE.put(
        {
            "id": job_id,
            "tenant_id": tenant_id,
            "source": source,
            "action_prefix": action_prefix,
            "events": events,
            "processor": processor,
            "max_attempts": ALLINO_EVENT_BUS_ASYNC_MAX_ATTEMPTS,
            "done": done,
        }
    )

    if not done.wait(timeout=ALLINO_EVENT_BUS_ASYNC_TIMEOUT_SECONDS):
        logger.warning("Async event-bus worker timeout, using direct fallback path")
        counts = processor(events, tenant_id, action_prefix)
        return counts, {
            "mode": EventBusMode.REDIS_FALLBACK,
            "reason": "worker_timeout",
            "published": len(events),
            "consumed": len(events),
            "queue_depth": _JOB_QUEUE.qsize(),
        }

    with _RESULT_LOCK:
        result = _JOB_RESULTS.pop(job_id, None)

    if not result:
        counts = processor(events, tenant_id, action_prefix)
        return counts, {
            "mode": EventBusMode.REDIS_FALLBACK,
            "reason": "worker_missing_result",
            "published": len(events),
            "consumed": len(events),
            "queue_depth": _JOB_QUEUE.qsize(),
        }

    if result.get("error"):
        counts = processor(events, tenant_id, action_prefix)
        return counts, {
            "mode": EventBusMode.REDIS_FALLBACK,
            "reason": "worker_error",
            "published": len(events),
            "consumed": len(events),
            "worker_attempts": int(result.get("attempts", 0)),
            "queue_depth": _JOB_QUEUE.qsize(),
        }

    counts = result["counts"]
    return counts, {
        "mode": EventBusMode.WORKER_ASYNC,
        "published": len(events),
        "consumed": int(counts.get("processed", 0)),
        "worker_attempts": int(result.get("attempts", 1)),
        "queue_depth": _JOB_QUEUE.qsize(),
    }


def _decode_stream_field(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _wait_for_external_worker_result(client: Any, result_key: str, timeout_seconds: float) -> dict[str, Any] | None:
    deadline = time() + max(0.1, timeout_seconds)
    while time() < deadline:
        payload = client.get(result_key)
        if payload:
            try:
                raw = _decode_stream_field(payload)
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
            except Exception:
                return None
        sleep(0.05)
    return None


def _process_with_external_worker(
    *,
    tenant_id: str,
    source: str,
    action_prefix: str,
    events: list[dict[str, Any]],
    processor: Callable[[list[dict[str, Any]], str, str], dict[str, int | float]],
) -> tuple[dict[str, int | float], dict[str, Any]]:
    if redis is None:
        counts = processor(events, tenant_id, action_prefix)
        return counts, {
            "mode": EventBusMode.REDIS_FALLBACK,
            "reason": "redis_not_installed",
            "published": 0,
            "consumed": len(events),
        }

    batch_id = str(uuid4())
    request_stream = f"{ALLINO_REDIS_STREAM_PREFIX}:requests"
    result_key = f"{ALLINO_REDIS_STREAM_PREFIX}:results:{batch_id}"

    try:
        client = redis.from_url(ALLINO_REDIS_URL, decode_responses=False)
        batch_size = len(events)
        for idx, event in enumerate(events):
            client.xadd(
                request_stream,
                {
                    "batch_id": batch_id,
                    "tenant_id": tenant_id,
                    "source": source,
                    "action_prefix": action_prefix,
                    "event_index": str(idx),
                    "batch_size": str(batch_size),
                    "raw_event": json.dumps(event, ensure_ascii=True),
                },
            )

        result = _wait_for_external_worker_result(
            client,
            result_key=result_key,
            timeout_seconds=ALLINO_EVENT_BUS_EXTERNAL_WORKER_TIMEOUT_SECONDS,
        )
        if not result:
            counts = processor(events, tenant_id, action_prefix)
            return counts, {
                "mode": EventBusMode.REDIS_FALLBACK,
                "reason": "external_worker_timeout",
                "published": len(events),
                "consumed": len(events),
            }

        if result.get("error"):
            counts = processor(events, tenant_id, action_prefix)
            return counts, {
                "mode": EventBusMode.REDIS_FALLBACK,
                "reason": "external_worker_error_result",
                "published": len(events),
                "consumed": len(events),
                "worker_attempts": int(result.get("attempts", 0)),
            }

        counts = {
            "processed": int(result.get("processed", 0)),
            "inserted": int(result.get("inserted", 0)),
            "duplicates": int(result.get("duplicates", 0)),
            "rejected": int(result.get("rejected", 0)),
            "total_lag_ms": float(result.get("total_lag_ms", 0.0)),
            "lag_samples": int(result.get("lag_samples", 0)),
        }
        return counts, {
            "mode": EventBusMode.EXTERNAL_WORKER,
            "published": len(events),
            "consumed": int(result.get("processed", 0)),
            "batch_id": batch_id,
            "worker_attempts": int(result.get("attempts", 1)),
        }
    except Exception as exc:  # pragma: no cover - resilience path
        logger.exception("External worker processing failed, using direct fallback: %s", exc)
        counts = processor(events, tenant_id, action_prefix)
        return counts, {
            "mode": EventBusMode.REDIS_FALLBACK,
            "reason": "external_worker_error",
            "published": len(events),
            "consumed": len(events),
        }


def process_connector_events(
    *,
    tenant_id: str,
    source: str,
    action_prefix: str,
    events: list[dict[str, Any]],
    processor: Callable[[list[dict[str, Any]], str, str], dict[str, int | float]],
) -> tuple[dict[str, int | float], dict[str, Any]]:
    """Process connector events either directly or through Redis Streams baseline path."""
    if not ALLINO_EVENT_BUS_ENABLED:
        counts = processor(events, tenant_id, action_prefix)
        return counts, {"mode": EventBusMode.DIRECT, "published": len(events), "consumed": len(events)}

    if ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED:
        return _process_with_external_worker(
            tenant_id=tenant_id,
            source=source,
            action_prefix=action_prefix,
            events=events,
            processor=processor,
        )

    if ALLINO_EVENT_BUS_ASYNC_CONSUMER_ENABLED:
        return _process_with_async_worker(
            tenant_id=tenant_id,
            source=source,
            action_prefix=action_prefix,
            events=events,
            processor=processor,
        )

    if redis is None:
        logger.warning("Event bus enabled but redis dependency is unavailable. Falling back to direct path.")
        counts = processor(events, tenant_id, action_prefix)
        return counts, {"mode": EventBusMode.REDIS_FALLBACK, "reason": "redis_not_installed", "published": 0, "consumed": len(events)}

    stream = f"{ALLINO_REDIS_STREAM_PREFIX}:{tenant_id}:{source}"
    try:
        client = redis.from_url(ALLINO_REDIS_URL, decode_responses=False)
        entry_ids: list[str] = []

        for event in events:
            entry_id = client.xadd(
                stream,
                {
                    "tenant_id": tenant_id,
                    "source": source,
                    "action_prefix": action_prefix,
                    "raw_event": json.dumps(event, ensure_ascii=True),
                },
            )
            entry_ids.append(_decode_stream_field(entry_id))

        consumed: list[dict[str, Any]] = []
        for entry_id in entry_ids:
            entries = client.xrange(stream, min=entry_id, max=entry_id, count=1)
            if not entries:
                continue
            fields = entries[0][1]
            raw_json = _decode_stream_field(fields.get(b"raw_event", fields.get("raw_event", b"{}")))
            try:
                payload = json.loads(raw_json)
                if isinstance(payload, dict):
                    consumed.append(payload)
            except json.JSONDecodeError:
                continue

        counts = processor(consumed, tenant_id, action_prefix)
        return counts, {
            "mode": EventBusMode.REDIS_STREAM,
            "stream": stream,
            "published": len(entry_ids),
            "consumed": len(consumed),
        }
    except Exception as exc:  # pragma: no cover - resilience path
        logger.exception("Redis stream processing failed, using direct fallback: %s", exc)
        counts = processor(events, tenant_id, action_prefix)
        return counts, {
            "mode": EventBusMode.REDIS_FALLBACK,
            "reason": "redis_error",
            "published": 0,
            "consumed": len(events),
        }
