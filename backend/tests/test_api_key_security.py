from fastapi import HTTPException
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core import security


def _generate_rsa_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return private_pem, public_pem


def test_require_api_key_allows_insecure_dev_when_explicitly_enabled(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", None)
    monkeypatch.setattr(security, "ALLINO_ENV", "development")
    monkeypatch.setattr(security, "ALLINO_ALLOW_INSECURE_DEV", True)

    security.require_api_key(x_api_key=None, authorization=None)


def test_require_api_key_rejects_when_insecure_dev_not_explicitly_enabled(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", None)
    monkeypatch.setattr(security, "ALLINO_ENV", "development")
    monkeypatch.setattr(security, "ALLINO_ALLOW_INSECURE_DEV", False)

    try:
        security.require_api_key(x_api_key=None, authorization=None)
    except HTTPException as exc:
        assert exc.status_code == 503
    else:  # pragma: no cover - explicit failure branch for readability
        raise AssertionError("Expected HTTPException 503 when insecure dev mode is not enabled")


def test_require_api_key_rejects_missing_config_outside_dev(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", None)
    monkeypatch.setattr(security, "ALLINO_ENV", "production")
    monkeypatch.setattr(security, "ALLINO_ALLOW_INSECURE_DEV", True)

    try:
        security.require_api_key(x_api_key=None, authorization=None)
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "ALLINO_API_KEY" in str(exc.detail)
        assert "ALLINO_JWT_SECRET" in str(exc.detail)
    else:  # pragma: no cover - explicit failure branch for readability
        raise AssertionError("Expected HTTPException 503 for misconfigured auth")


def test_require_api_key_enforces_header_when_key_is_configured(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", "secret")
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", None)
    monkeypatch.setattr(security, "ALLINO_ENV", "development")
    monkeypatch.setattr(security, "ALLINO_ALLOW_INSECURE_DEV", True)

    try:
        security.require_api_key(x_api_key="wrong", authorization=None)
    except HTTPException as exc:
        assert exc.status_code == 401
    else:  # pragma: no cover - explicit failure branch for readability
        raise AssertionError("Expected HTTPException 401 for wrong API key")

    security.require_api_key(x_api_key="secret", authorization=None)


def test_require_api_key_accepts_valid_jwt_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)

    token = jwt.encode({"sub": "user-1"}, "jwt-secret", algorithm="HS256")
    security.require_api_key(x_api_key=None, authorization=f"Bearer {token}")


def test_require_api_key_rejects_invalid_jwt(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)

    bad_token = jwt.encode({"sub": "user-1"}, "wrong-secret", algorithm="HS256")
    try:
        security.require_api_key(x_api_key=None, authorization=f"Bearer {bad_token}")
    except HTTPException as exc:
        assert exc.status_code == 401
    else:  # pragma: no cover - explicit failure branch for readability
        raise AssertionError("Expected HTTPException 401 for invalid JWT")


def test_require_api_key_accepts_api_key_or_jwt_when_both_enabled(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", "api-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)

    security.require_api_key(x_api_key="api-secret", authorization=None)

    token = jwt.encode({"sub": "user-2"}, "jwt-secret", algorithm="HS256")
    security.require_api_key(x_api_key="wrong", authorization=f"Bearer {token}")


def test_require_connector_sync_permission_accepts_allowed_role(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_ROLES", {"admin", "operator"})
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_SCOPES", {"connectors:sync"})

    token = jwt.encode({"sub": "u", "roles": ["operator"]}, "jwt-secret", algorithm="HS256")
    security.require_connector_sync_permission(
        x_api_key=None,
        authorization=f"Bearer {token}",
    )


def test_require_connector_sync_permission_accepts_allowed_scope(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_ROLES", {"admin"})
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_SCOPES", {"connectors:sync", "sync:connectors"})

    token = jwt.encode({"sub": "u", "scope": "read connectors:sync"}, "jwt-secret", algorithm="HS256")
    security.require_connector_sync_permission(
        x_api_key=None,
        authorization=f"Bearer {token}",
    )


def test_require_connector_sync_permission_rejects_missing_claims(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_ROLES", {"admin"})
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_SCOPES", {"connectors:sync"})

    token = jwt.encode({"sub": "u", "scope": "read:only"}, "jwt-secret", algorithm="HS256")
    try:
        security.require_connector_sync_permission(
            x_api_key=None,
            authorization=f"Bearer {token}",
        )
    except HTTPException as exc:
        assert exc.status_code == 403
    else:  # pragma: no cover
        raise AssertionError("Expected HTTPException 403 for missing sync permission")


def test_require_connector_sync_permission_allows_valid_api_key_without_jwt_claims(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", "api-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_ROLES", {"admin"})
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_SCOPES", {"connectors:sync"})

    security.require_connector_sync_permission(
        x_api_key="api-secret",
        authorization=None,
    )


def test_require_ingestion_read_permission_accepts_allowed_role(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_READ_ROLES", {"viewer", "analyst"})
    monkeypatch.setattr(security, "ALLINO_JWT_READ_SCOPES", {"ingestion:read"})

    token = jwt.encode({"sub": "u", "roles": ["viewer"]}, "jwt-secret", algorithm="HS256")
    security.require_ingestion_read_permission(
        x_api_key=None,
        authorization=f"Bearer {token}",
    )


def test_require_ingestion_read_permission_accepts_allowed_scope(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_READ_ROLES", {"viewer"})
    monkeypatch.setattr(security, "ALLINO_JWT_READ_SCOPES", {"inbox:read", "metrics:read"})

    token = jwt.encode({"sub": "u", "scope": "foo inbox:read"}, "jwt-secret", algorithm="HS256")
    security.require_ingestion_read_permission(
        x_api_key=None,
        authorization=f"Bearer {token}",
    )


def test_require_ingestion_read_permission_rejects_missing_claims(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_READ_ROLES", {"viewer"})
    monkeypatch.setattr(security, "ALLINO_JWT_READ_SCOPES", {"inbox:read"})

    token = jwt.encode({"sub": "u", "scope": "sync:connectors"}, "jwt-secret", algorithm="HS256")
    try:
        security.require_ingestion_read_permission(
            x_api_key=None,
            authorization=f"Bearer {token}",
        )
    except HTTPException as exc:
        assert exc.status_code == 403
    else:  # pragma: no cover
        raise AssertionError("Expected HTTPException 403 for missing read permission")


def test_require_ingestion_read_permission_allows_valid_api_key(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", "api-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_READ_ROLES", {"viewer"})
    monkeypatch.setattr(security, "ALLINO_JWT_READ_SCOPES", {"inbox:read"})

    security.require_ingestion_read_permission(
        x_api_key="api-secret",
        authorization=None,
    )


def test_require_api_key_accepts_valid_rs256_jwt_when_configured(monkeypatch) -> None:
    private_pem, public_pem = _generate_rsa_keypair()
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", None)
    monkeypatch.setattr(security, "ALLINO_JWT_PUBLIC_KEY", public_pem)
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "RS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)

    token = jwt.encode({"sub": "user-rs256"}, private_pem, algorithm="RS256")
    security.require_api_key(x_api_key=None, authorization=f"Bearer {token}")


def test_require_api_key_rejects_rs256_jwt_signed_by_different_key(monkeypatch) -> None:
    _, public_pem = _generate_rsa_keypair()
    other_private_pem, _ = _generate_rsa_keypair()
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", None)
    monkeypatch.setattr(security, "ALLINO_JWT_PUBLIC_KEY", public_pem)
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "RS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)

    token = jwt.encode({"sub": "attacker"}, other_private_pem, algorithm="RS256")
    try:
        security.require_api_key(x_api_key=None, authorization=f"Bearer {token}")
    except HTTPException as exc:
        assert exc.status_code == 401
    else:  # pragma: no cover
        raise AssertionError("Expected HTTPException 401 for RS256 token signed by wrong key")


def test_require_api_key_rejects_rs256_when_public_key_missing(monkeypatch) -> None:
    private_pem, _ = _generate_rsa_keypair()
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", None)
    monkeypatch.setattr(security, "ALLINO_JWT_PUBLIC_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "RS256")
    monkeypatch.setattr(security, "ALLINO_ENV", "production")
    monkeypatch.setattr(security, "ALLINO_ALLOW_INSECURE_DEV", False)

    token = jwt.encode({"sub": "user-rs256"}, private_pem, algorithm="RS256")
    try:
        security.require_api_key(x_api_key=None, authorization=f"Bearer {token}")
    except HTTPException as exc:
        assert exc.status_code == 503
    else:  # pragma: no cover
        raise AssertionError("Expected HTTPException 503 when no verification key is configured at all")


def test_require_connector_sync_permission_accepts_rs256_role_claim(monkeypatch) -> None:
    private_pem, public_pem = _generate_rsa_keypair()
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", None)
    monkeypatch.setattr(security, "ALLINO_JWT_PUBLIC_KEY", public_pem)
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "RS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_ROLES", {"admin", "operator"})
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_SCOPES", {"connectors:sync"})

    token = jwt.encode({"sub": "u", "roles": ["operator"]}, private_pem, algorithm="RS256")
    security.require_connector_sync_permission(
        x_api_key=None,
        authorization=f"Bearer {token}",
    )
