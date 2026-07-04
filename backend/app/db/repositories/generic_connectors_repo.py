import json
from typing import Any

from ..session import get_connection


def create_generic_connector(
    *,
    config_id: str,
    tenant_id: str,
    name: str,
    slug: str,
    base_url: str | None,
    auth_method: str,
    auth_header_name: str | None,
    poll_interval_seconds: int | None,
    field_mapping: dict[str, Any],
    webhook_enabled: bool,
) -> dict[str, Any]:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO generic_connector_configs (
                id, tenant_id, name, slug, base_url, auth_method, auth_header_name,
                poll_interval_seconds, field_mapping, webhook_enabled, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """,
            (
                config_id,
                tenant_id,
                name,
                slug,
                base_url,
                auth_method,
                auth_header_name,
                poll_interval_seconds,
                json.dumps(field_mapping),
                1 if webhook_enabled else 0,
            ),
        )
        conn.commit()

    return get_generic_connector(config_id=config_id, tenant_id=tenant_id)  # type: ignore[return-value]


_UPDATABLE_FIELDS = (
    "base_url",
    "auth_method",
    "auth_header_name",
    "poll_interval_seconds",
    "field_mapping",
    "webhook_enabled",
)


def update_generic_connector(
    *,
    config_id: str,
    tenant_id: str,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    set_clauses: list[str] = []
    values: list[Any] = []
    for key in _UPDATABLE_FIELDS:
        if key not in updates:
            continue
        value = updates[key]
        if key == "field_mapping":
            value = json.dumps(value)
        elif key == "webhook_enabled":
            value = 1 if value else 0
        set_clauses.append(f"{key} = ?")
        values.append(value)

    if not set_clauses:
        return get_generic_connector(config_id=config_id, tenant_id=tenant_id)

    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    values.extend([config_id, tenant_id])

    with get_connection() as conn:
        cursor = conn.execute(
            f"UPDATE generic_connector_configs SET {', '.join(set_clauses)} "
            "WHERE id = ? AND tenant_id = ?",
            values,
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None

    return get_generic_connector(config_id=config_id, tenant_id=tenant_id)


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "tenant_id": row["tenant_id"],
        "name": row["name"],
        "slug": row["slug"],
        "base_url": row["base_url"],
        "auth_method": row["auth_method"],
        "auth_header_name": row["auth_header_name"],
        "poll_interval_seconds": row["poll_interval_seconds"],
        "field_mapping": json.loads(row["field_mapping"]),
        "webhook_enabled": bool(row["webhook_enabled"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_generic_connectors(*, tenant_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, tenant_id, name, slug, base_url, auth_method, auth_header_name,
                   poll_interval_seconds, field_mapping, webhook_enabled, status,
                   created_at, updated_at
            FROM generic_connector_configs
            WHERE tenant_id = ?
            ORDER BY created_at ASC
            """,
            (tenant_id,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_generic_connectors_with_polling() -> list[dict[str, Any]]:
    """Active generic connectors across all tenants that have poll_interval_seconds set.
    Used by the scheduler worker, which runs outside any single tenant's request context."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, tenant_id, name, slug, base_url, auth_method, auth_header_name,
                   poll_interval_seconds, field_mapping, webhook_enabled, status,
                   created_at, updated_at
            FROM generic_connector_configs
            WHERE status = 'active' AND poll_interval_seconds IS NOT NULL
            ORDER BY tenant_id ASC, created_at ASC
            """
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_generic_connector(*, config_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    with get_connection() as conn:
        if tenant_id is not None:
            row = conn.execute(
                """
                SELECT id, tenant_id, name, slug, base_url, auth_method, auth_header_name,
                       poll_interval_seconds, field_mapping, webhook_enabled, status,
                       created_at, updated_at
                FROM generic_connector_configs
                WHERE id = ? AND tenant_id = ?
                """,
                (config_id, tenant_id),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT id, tenant_id, name, slug, base_url, auth_method, auth_header_name,
                       poll_interval_seconds, field_mapping, webhook_enabled, status,
                       created_at, updated_at
                FROM generic_connector_configs
                WHERE id = ?
                """,
                (config_id,),
            ).fetchone()

    if row is None:
        return None
    return _row_to_dict(row)


def delete_generic_connector(*, config_id: str, tenant_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM generic_connector_configs WHERE id = ? AND tenant_id = ?",
            (config_id, tenant_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def slug_exists(*, tenant_id: str, slug: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM generic_connector_configs WHERE tenant_id = ? AND slug = ?",
            (tenant_id, slug),
        ).fetchone()
    return row is not None
