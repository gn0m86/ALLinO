from __future__ import annotations

import argparse
import json
import time

import httpx
import redis


def run_dlq_smoke(
    *,
    backend_url: str,
    tenant_id: str,
    api_key: str,
    redis_url: str,
    dlq_stream: str,
    output_path: str,
) -> int:
    client = redis.from_url(redis_url, decode_responses=True)
    before = int(client.xlen(dlq_stream) or 0)

    headers = {
        "X-API-Key": api_key,
        "X-Tenant-Id": tenant_id,
    }
    payload = {
        "retry_max_attempts": 1,
        "retry_backoff_seconds": 0.0,
        "seeded_events": [
            {
                "id": "stg-dlq-zoom-1",
                "uuid": "stg-dlq-zoom-uuid-1",
                "topic": "DLQ smoke",
                "host_email": "ops@example.com",
                "start_time": "2026-07-01T11:30:00Z",
            }
        ],
    }

    response = httpx.post(
        f"{backend_url}/api/v1/ingestion/connectors/zoom/sync?tenant_id={tenant_id}",
        headers=headers,
        json=payload,
        timeout=15.0,
    )

    after = before
    for _ in range(20):
        after = int(client.xlen(dlq_stream) or 0)
        if after > before:
            break
        time.sleep(0.15)

    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    result = {
        "status_code": response.status_code,
        "event_bus": body.get("event_bus"),
        "before_dlq": before,
        "after_dlq": after,
        "dlq_delta": after - before,
        "expected_fallback_reason": "external_worker_error_result",
        "observed_reason": body.get("reason"),
        "ok": response.status_code == 200
        and body.get("event_bus") == "redis_fallback"
        and body.get("reason") == "external_worker_error_result"
        and (after - before) > 0,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return 0 if result["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="ALLinO external worker DLQ smoke")
    parser.add_argument("--backend-url", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--redis-url", required=True)
    parser.add_argument("--dlq-stream", default="allino:ingestion:dlq")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    return run_dlq_smoke(
        backend_url=args.backend_url,
        tenant_id=args.tenant_id,
        api_key=args.api_key,
        redis_url=args.redis_url,
        dlq_stream=args.dlq_stream,
        output_path=args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
