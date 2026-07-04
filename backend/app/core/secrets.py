from __future__ import annotations

import os
from typing import Any

import httpx


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _vault_enabled() -> bool:
    return os.getenv("ALLINO_VAULT_ENABLED", "false").strip().lower() in _TRUE_VALUES


def _fetch_from_vault(key: str) -> str | None:
    if not _vault_enabled():
        return None

    addr = (os.getenv("ALLINO_VAULT_ADDR") or "").strip()
    token = (os.getenv("ALLINO_VAULT_TOKEN") or "").strip()
    mount = (os.getenv("ALLINO_VAULT_MOUNT") or "secret").strip().strip("/")
    path = (os.getenv("ALLINO_VAULT_PATH") or "allino").strip().strip("/")

    if not addr or not token:
        return None

    url = f"{addr.rstrip('/')}/v1/{mount}/data/{path}"
    try:
        response = httpx.get(
            url,
            headers={"X-Vault-Token": token},
            timeout=2.0,
        )
        response.raise_for_status()
    except Exception:
        return None

    try:
        payload: dict[str, Any] = response.json()
        data = payload.get("data") or {}
        nested = data.get("data") or {}
        value = nested.get(key)
    except Exception:
        return None

    if value is None:
        return None
    return str(value)


def get_secret_value(key: str) -> str | None:
    env_value = os.getenv(key)
    if env_value:
        return env_value
    return _fetch_from_vault(key)


def has_secret_value(key: str) -> bool:
    value = get_secret_value(key)
    return bool(value and value.strip())
