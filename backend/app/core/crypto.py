from __future__ import annotations

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from .config import ALLINO_ENCRYPTION_AT_REST_ENABLED, ALLINO_ENCRYPTION_KEY, ALLINO_ENV

_ENC_PREFIX = "enc:v1:"
_CACHED_FERNET: Optional[Fernet] = None


def _build_fernet_key(raw_key: str) -> bytes:
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Optional[Fernet]:
    global _CACHED_FERNET
    if _CACHED_FERNET is not None:
        return _CACHED_FERNET

    key = (ALLINO_ENCRYPTION_KEY or "").strip()
    if not key:
        return None

    _CACHED_FERNET = Fernet(_build_fernet_key(key))
    return _CACHED_FERNET


def validate_encryption_configuration() -> None:
    if ALLINO_ENV == "production" and ALLINO_ENCRYPTION_AT_REST_ENABLED and not (ALLINO_ENCRYPTION_KEY or "").strip():
        raise RuntimeError(
            "ALLINO_ENCRYPTION_AT_REST_ENABLED=true in production requires ALLINO_ENCRYPTION_KEY"
        )


def encrypt_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not ALLINO_ENCRYPTION_AT_REST_ENABLED:
        return value
    if value.startswith(_ENC_PREFIX):
        return value

    fernet = _get_fernet()
    if fernet is None:
        return value

    token = fernet.encrypt(value.encode("utf-8")).decode("ascii")
    return f"{_ENC_PREFIX}{token}"


def decrypt_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not value.startswith(_ENC_PREFIX):
        return value

    token = value[len(_ENC_PREFIX):]
    fernet = _get_fernet()
    if fernet is None:
        return value

    try:
        return fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return value
