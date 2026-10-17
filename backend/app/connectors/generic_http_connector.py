from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from ..core.secrets import get_secret_value
from .base import BaseConnector, ConnectorHealth, RetryPolicy


def slug_to_env_key(slug: str) -> str:
    """POSIX env var names can't contain '-', but connector slugs can (derived from a free-text name)."""
    return slug.upper().replace("-", "_")


def extract_path(item: dict[str, Any], path: str) -> Any:
    """Extract a value from a nested dict/list via a dot-separated path.

    A segment that is a plain non-negative integer indexes into a list at that
    point (e.g. "contacts.0.profile.name" for a WhatsApp-shaped payload item).
    """
    value: Any = item
    for part in path.split("."):
        if isinstance(value, list):
            if not part.isdigit() or int(part) >= len(value):
                return None
            value = value[int(part)]
        elif isinstance(value, dict):
            if part not in value:
                return None
            value = value[part]
        else:
            return None
    return value


def extract_items_from_payload(payload: Any, items_path: str | None = None) -> list[dict[str, Any]]:
    """Normalize a poll response or webhook body into a flat list of raw item dicts.

    `items_path`, when given, locates a list of items nested deeper than a top-level
    array or an "items"/"data"/"results" key — needed for sources like the WhatsApp
    Business Cloud API, whose messages live at `entry[].changes[].value.messages[]`.
    Each `[]`-suffixed dot-separated segment iterates a list and flattens one level;
    a plain segment is a dict key. Without `items_path`, falls back to the original
    flat-payload heuristics (fully backward compatible with existing connectors).
    """
    if items_path:
        values: list[Any] = [payload]
        for part in items_path.split("."):
            is_array = part.endswith("[]")
            key = part[:-2] if is_array else part
            next_values: list[Any] = []
            for value in values:
                if not isinstance(value, dict) or key not in value:
                    continue
                nested = value[key]
                if is_array:
                    if isinstance(nested, list):
                        next_values.extend(nested)
                else:
                    next_values.append(nested)
            values = next_values
        return [item for item in values if isinstance(item, dict)]

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    return []


def _parse_timestamp(raw: Any) -> datetime:
    if isinstance(raw, (int, float)):
        # Some sources (e.g. Viber) send epoch milliseconds, not seconds.
        seconds = raw / 1000 if raw > 1e12 else raw
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return datetime.now(timezone.utc)
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def map_generic_item_to_unified_event(
    item: dict[str, Any],
    *,
    tenant_id: str,
    slug: str,
    field_mapping: dict[str, Any],
) -> dict[str, Any]:
    external_id_raw = extract_path(item, field_mapping["externalId"])
    if external_id_raw is None:
        raise ValueError(f"generic connector '{slug}' item missing externalId field")
    external_id = str(external_id_raw)

    timestamp_raw = extract_path(item, field_mapping["timestamp"])
    timestamp = _parse_timestamp(timestamp_raw)

    preview = ""
    preview_path = field_mapping.get("preview")
    if preview_path:
        preview_raw = extract_path(item, preview_path)
        if preview_raw is not None:
            preview = str(preview_raw)

    return {
        "eventId": f"generic-{slug}-{external_id}",
        "tenantId": tenant_id,
        "sourceType": f"generic:{slug}",
        "externalId": external_id,
        "timestamp": timestamp.isoformat(),
        "payload": {"text": preview, "identifier": external_id},
        "schemaVersion": "1.0.0",
    }


class GenericHttpConnector(BaseConnector):
    def __init__(
        self,
        *,
        tenant_id: str,
        slug: str,
        base_url: str | None,
        auth_method: str,
        auth_header_name: str | None,
        field_mapping: dict[str, Any],
        retry_policy: RetryPolicy | None = None,
        seeded_items: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(source=f"generic:{slug}", retry_policy=retry_policy)
        self.tenant_id = tenant_id
        self.slug = slug
        self.base_url = base_url
        self.auth_method = auth_method
        self.auth_header_name = auth_header_name
        self.field_mapping = field_mapping
        self.token = get_secret_value(f"ALLINO_GENERIC_{slug_to_env_key(slug)}_TOKEN")
        self._started = False
        self._seeded_items = seeded_items or []

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def health(self) -> ConnectorHealth:
        if not self._started:
            status = "stopped"
        elif self._seeded_items or self.base_url:
            status = "healthy"
        else:
            status = "degraded"

        return ConnectorHealth(
            status=status,
            source=self.source,
            details={
                "auth_method": self.auth_method,
                "has_token": bool(self.token),
                "base_url": self.base_url,
                "seeded_items": len(self._seeded_items),
                "retry_count": self.last_retry_count,
            },
        )

    def fetch_events(self, cursor: str | None = None) -> Iterable[dict[str, Any]]:
        if not self._started:
            return []

        items = self._seeded_items
        if not items and self.base_url:
            items = self.run_with_retry(self._fetch_items)

        return [
            map_generic_item_to_unified_event(
                item, tenant_id=self.tenant_id, slug=self.slug, field_mapping=self.field_mapping
            )
            for item in items
        ]

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "allino-backend"}
        if self.auth_method == "bearer" and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.auth_method == "api_key" and self.token and self.auth_header_name:
            headers[self.auth_header_name] = self.token
        elif self.auth_method == "basic" and self.token:
            headers["Authorization"] = f"Basic {self.token}"
        return headers

    def _fetch_items(self) -> list[dict[str, Any]]:
        if not self.base_url:
            return []
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(self.base_url, headers=self._build_headers())
            resp.raise_for_status()
            payload = resp.json()
        return extract_items_from_payload(payload, self.field_mapping.get("items_path"))
