from app.db import session
from app.db.session import init_db
from app.db.repositories.generic_connectors_repo import (
    create_generic_connector,
    get_generic_connector,
    update_generic_connector,
)


def _create(tmp_path, db_name: str) -> dict:
    session.DB_PATH = tmp_path / db_name
    init_db()
    return create_generic_connector(
        config_id="cfg-1",
        tenant_id="tenant_demo",
        name="My Jenkins",
        slug="my-jenkins",
        base_url="https://old.example.invalid",
        auth_method="none",
        auth_header_name=None,
        poll_interval_seconds=300,
        field_mapping={"externalId": "id", "timestamp": "updated_at", "preview": "title"},
        webhook_enabled=False,
    )


def test_update_generic_connector_partial_update_leaves_other_fields(tmp_path) -> None:
    created = _create(tmp_path, "generic_repo_partial_update.db")

    updated = update_generic_connector(
        config_id=created["id"],
        tenant_id="tenant_demo",
        updates={"base_url": "https://new.example.invalid"},
    )

    assert updated is not None
    assert updated["base_url"] == "https://new.example.invalid"
    assert updated["poll_interval_seconds"] == 300
    assert updated["auth_method"] == "none"
    assert updated["field_mapping"] == created["field_mapping"]
    assert updated["updated_at"] is not None


def test_update_generic_connector_field_mapping_and_webhook(tmp_path) -> None:
    created = _create(tmp_path, "generic_repo_mapping_update.db")

    updated = update_generic_connector(
        config_id=created["id"],
        tenant_id="tenant_demo",
        updates={
            "field_mapping": {"externalId": "uuid", "timestamp": "ts"},
            "webhook_enabled": True,
        },
    )

    assert updated is not None
    assert updated["field_mapping"] == {"externalId": "uuid", "timestamp": "ts"}
    assert updated["webhook_enabled"] is True


def test_update_generic_connector_ignores_unknown_fields(tmp_path) -> None:
    created = _create(tmp_path, "generic_repo_unknown_field.db")

    updated = update_generic_connector(
        config_id=created["id"],
        tenant_id="tenant_demo",
        updates={"name": "Renamed", "slug": "renamed"},
    )

    assert updated is not None
    assert updated["name"] == "My Jenkins"
    assert updated["slug"] == "my-jenkins"


def test_update_generic_connector_nonexistent_id_returns_none(tmp_path) -> None:
    session.DB_PATH = tmp_path / "generic_repo_missing.db"
    init_db()

    result = update_generic_connector(
        config_id="does-not-exist",
        tenant_id="tenant_demo",
        updates={"base_url": "https://example.invalid"},
    )

    assert result is None


def test_update_generic_connector_wrong_tenant_returns_none(tmp_path) -> None:
    created = _create(tmp_path, "generic_repo_wrong_tenant.db")

    result = update_generic_connector(
        config_id=created["id"],
        tenant_id="tenant_other",
        updates={"base_url": "https://example.invalid"},
    )

    assert result is None
    unchanged = get_generic_connector(config_id=created["id"], tenant_id="tenant_demo")
    assert unchanged["base_url"] == "https://old.example.invalid"


def test_update_generic_connector_empty_updates_returns_unchanged(tmp_path) -> None:
    created = _create(tmp_path, "generic_repo_empty_updates.db")

    result = update_generic_connector(
        config_id=created["id"],
        tenant_id="tenant_demo",
        updates={},
    )

    assert result is not None
    assert result["base_url"] == created["base_url"]
