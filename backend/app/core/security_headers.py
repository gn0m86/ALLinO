from __future__ import annotations

from fastapi import Request

from .config import (
    ALLINO_CSP_POLICY,
    ALLINO_HSTS_ENABLED,
    ALLINO_HSTS_INCLUDE_SUBDOMAINS,
    ALLINO_HSTS_MAX_AGE,
    ALLINO_HSTS_PRELOAD,
    ALLINO_SECURITY_HEADERS_ENABLED,
)


def _is_https_request(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
    if forwarded_proto:
        return forwarded_proto == "https"
    return request.url.scheme == "https"


def _hsts_value() -> str:
    parts = [f"max-age={ALLINO_HSTS_MAX_AGE}"]
    if ALLINO_HSTS_INCLUDE_SUBDOMAINS:
        parts.append("includeSubDomains")
    if ALLINO_HSTS_PRELOAD:
        parts.append("preload")
    return "; ".join(parts)


def build_security_headers(request: Request) -> dict[str, str]:
    if not ALLINO_SECURITY_HEADERS_ENABLED:
        return {}

    headers = {
        "Content-Security-Policy": ALLINO_CSP_POLICY,
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }

    if ALLINO_HSTS_ENABLED and _is_https_request(request):
        headers["Strict-Transport-Security"] = _hsts_value()

    return headers
