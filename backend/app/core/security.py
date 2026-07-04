import logging

from fastapi import Header, HTTPException
import jwt
import pyotp
from jwt import InvalidTokenError

from .config import (
    ALLINO_ALLOW_INSECURE_DEV,
    ALLINO_API_KEY,
    ALLINO_ENV,
    ALLINO_JWT_ADMIN_ROLES,
    ALLINO_JWT_ADMIN_SCOPES,
    ALLINO_JWT_ALGORITHM,
    ALLINO_JWT_AUDIENCE,
    ALLINO_JWT_ISSUER,
    ALLINO_JWT_MESSAGE_ACTIONS_ROLES,
    ALLINO_JWT_MESSAGE_ACTIONS_SCOPES,
    ALLINO_JWT_PUBLIC_KEY,
    ALLINO_JWT_READ_ROLES,
    ALLINO_JWT_READ_SCOPES,
    ALLINO_JWT_REPLY_ROLES,
    ALLINO_JWT_REPLY_SCOPES,
    ALLINO_JWT_SECRET,
    ALLINO_JWT_SYNC_ROLES,
    ALLINO_JWT_SYNC_SCOPES,
)
from .secrets import get_secret_value

logger = logging.getLogger(__name__)

_ASYMMETRIC_ALG_PREFIXES = ("RS", "ES", "PS")


def _is_asymmetric_algorithm(algorithm: str) -> bool:
    return algorithm.upper().startswith(_ASYMMETRIC_ALG_PREFIXES)


def _jwt_verification_key() -> str | None:
    """Key material used to verify inbound JWTs. RS*/ES*/PS* use the configured
    public key (this service only verifies tokens issued elsewhere, so a
    private key is never needed here); HS* uses the shared secret."""
    if _is_asymmetric_algorithm(ALLINO_JWT_ALGORITHM):
        if not ALLINO_JWT_PUBLIC_KEY:
            return None
        return ALLINO_JWT_PUBLIC_KEY.replace("\\n", "\n")
    return ALLINO_JWT_SECRET


if not ALLINO_API_KEY and not _jwt_verification_key():
    logger.warning(
        "No auth secret configured. env=%s, allow_insecure_dev=%s",
        ALLINO_ENV,
        ALLINO_ALLOW_INSECURE_DEV,
    )


def _decode_jwt(token: str) -> dict:
    key = _jwt_verification_key()
    if not key:
        raise InvalidTokenError("JWT verification key not configured")
    decode_kwargs: dict = {
        "algorithms": [ALLINO_JWT_ALGORITHM],
    }
    if ALLINO_JWT_ISSUER:
        decode_kwargs["issuer"] = ALLINO_JWT_ISSUER
    if ALLINO_JWT_AUDIENCE:
        decode_kwargs["audience"] = ALLINO_JWT_AUDIENCE
    else:
        decode_kwargs["options"] = {"verify_aud": False}
    return jwt.decode(token, key, **decode_kwargs)


def _is_valid_bearer(authorization: str | None) -> bool:
    if not authorization:
        return False
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        return False
    token = parts[1].strip()
    try:
        _decode_jwt(token)
    except InvalidTokenError:
        return False
    return True


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        return None
    return parts[1].strip()


def get_authenticated_jwt_payload(authorization: str | None) -> dict | None:
    """Decode and return JWT payload for Bearer auth, or None when JWT auth is not used."""
    if not _jwt_verification_key():
        return None

    token = _extract_bearer_token(authorization)
    if not token:
        return None

    try:
        return _decode_jwt(token)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token") from exc


def _claim_values(payload: dict, key: str) -> set[str]:
    raw = payload.get(key)
    if isinstance(raw, str):
        items = raw.split() if key in {"scope", "scp"} else [raw]
        return {i.strip().lower() for i in items if i and i.strip()}
    if isinstance(raw, list):
        return {str(i).strip().lower() for i in raw if str(i).strip()}
    return set()


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """Enforce API key and/or JWT, fail-closed outside explicitly allowed local dev mode."""
    has_api_key = bool(ALLINO_API_KEY)
    has_jwt = bool(_jwt_verification_key())

    if not has_api_key and not has_jwt:
        if ALLINO_ENV == "development" and ALLINO_ALLOW_INSECURE_DEV:
            return
        raise HTTPException(
            status_code=503,
            detail=(
                "Server auth misconfigured: set ALLINO_API_KEY, ALLINO_JWT_SECRET, "
                "or ALLINO_JWT_PUBLIC_KEY (for RS*/ES*/PS* algorithms)"
            ),
        )

    if has_api_key and x_api_key == ALLINO_API_KEY:
        return

    if has_jwt and _is_valid_bearer(authorization):
        return

    raise HTTPException(status_code=401, detail="Invalid or missing authentication credentials")


def require_connector_sync_permission(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """Require connector-sync permissions for JWT callers; API key callers are trusted operational users."""
    require_api_key(x_api_key=x_api_key, authorization=authorization)

    if ALLINO_API_KEY and x_api_key == ALLINO_API_KEY:
        return

    # In API-key-only or local insecure-dev mode, auth was already enforced by require_api_key.
    if not _jwt_verification_key():
        return

    payload = get_authenticated_jwt_payload(authorization)
    if payload is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    roles = _claim_values(payload, "role") | _claim_values(payload, "roles")
    scopes = _claim_values(payload, "scope") | _claim_values(payload, "scp")

    if roles & ALLINO_JWT_SYNC_ROLES:
        return
    if scopes & ALLINO_JWT_SYNC_SCOPES:
        return

    raise HTTPException(status_code=403, detail="Insufficient permissions for connector sync")


def require_ingestion_read_permission(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """Require read permissions for JWT callers on ingestion read endpoints; API key callers are trusted."""
    require_api_key(x_api_key=x_api_key, authorization=authorization)

    if ALLINO_API_KEY and x_api_key == ALLINO_API_KEY:
        return

    # In API-key-only or local insecure-dev mode, auth was already enforced by require_api_key.
    if not _jwt_verification_key():
        return

    payload = get_authenticated_jwt_payload(authorization)
    if payload is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    roles = _claim_values(payload, "role") | _claim_values(payload, "roles")
    scopes = _claim_values(payload, "scope") | _claim_values(payload, "scp")

    if roles & ALLINO_JWT_READ_ROLES:
        return
    if scopes & ALLINO_JWT_READ_SCOPES:
        return

    raise HTTPException(status_code=403, detail="Insufficient permissions for ingestion read endpoints")


def require_reply_permission(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """Require reply/write-back permissions for JWT callers; API key callers are trusted."""
    require_api_key(x_api_key=x_api_key, authorization=authorization)

    if ALLINO_API_KEY and x_api_key == ALLINO_API_KEY:
        return

    # In API-key-only or local insecure-dev mode, auth was already enforced by require_api_key.
    if not _jwt_verification_key():
        return

    payload = get_authenticated_jwt_payload(authorization)
    if payload is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    roles = _claim_values(payload, "role") | _claim_values(payload, "roles")
    scopes = _claim_values(payload, "scope") | _claim_values(payload, "scp")

    if roles & ALLINO_JWT_REPLY_ROLES:
        return
    if scopes & ALLINO_JWT_REPLY_SCOPES:
        return

    raise HTTPException(status_code=403, detail="Insufficient permissions for message reply")


def require_message_actions_permission(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """Require archive/snooze permissions for JWT callers; API key callers are trusted."""
    require_api_key(x_api_key=x_api_key, authorization=authorization)

    if ALLINO_API_KEY and x_api_key == ALLINO_API_KEY:
        return

    # In API-key-only or local insecure-dev mode, auth was already enforced by require_api_key.
    if not _jwt_verification_key():
        return

    payload = get_authenticated_jwt_payload(authorization)
    if payload is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    roles = _claim_values(payload, "role") | _claim_values(payload, "roles")
    scopes = _claim_values(payload, "scope") | _claim_values(payload, "scp")

    if roles & ALLINO_JWT_MESSAGE_ACTIONS_ROLES:
        return
    if scopes & ALLINO_JWT_MESSAGE_ACTIONS_SCOPES:
        return

    raise HTTPException(status_code=403, detail="Insufficient permissions for message actions")


def require_admin_mfa_permission(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_totp_code: str | None = Header(default=None, alias="X-TOTP-Code"),
) -> None:
    """Require admin-tier permissions PLUS a valid TOTP code, for destructive admin
    actions. Unlike every other tier, the TOTP check below is NOT skipped for
    API-key callers -- the entire point of a second factor is that it applies
    regardless of which first factor authenticated the caller."""
    require_api_key(x_api_key=x_api_key, authorization=authorization)

    is_trusted_api_key = bool(ALLINO_API_KEY) and x_api_key == ALLINO_API_KEY
    if not is_trusted_api_key and _jwt_verification_key():
        payload = get_authenticated_jwt_payload(authorization)
        if payload is None:
            raise HTTPException(status_code=401, detail="Missing bearer token")

        roles = _claim_values(payload, "role") | _claim_values(payload, "roles")
        scopes = _claim_values(payload, "scope") | _claim_values(payload, "scp")

        if not (roles & ALLINO_JWT_ADMIN_ROLES or scopes & ALLINO_JWT_ADMIN_SCOPES):
            raise HTTPException(status_code=403, detail="Insufficient permissions for admin actions")

    secret = get_secret_value("ALLINO_ADMIN_TOTP_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="Admin MFA is not configured")
    if not x_totp_code:
        raise HTTPException(status_code=401, detail="Missing TOTP code")
    if not pyotp.TOTP(secret).verify(x_totp_code, valid_window=1):
        raise HTTPException(status_code=403, detail="Invalid TOTP code")
