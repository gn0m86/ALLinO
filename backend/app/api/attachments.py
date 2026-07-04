import os
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response

from ..core.secrets import get_secret_value
from ..core.security import require_ingestion_read_permission
from ..core.tenant import resolve_tenant_id
from ..db.repositories.messages_repo import get_message

router = APIRouter(prefix="/api/v1/ingestion", tags=["attachments"])

# Opt-in ("click to load") media only, never auto-fetched during sync -- fetched
# fresh on every request, not cached to disk, so there's no persistent plaintext
# copy of message media at rest.
_MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


def _fetch_rocketchat_attachment(attachment_ref: str, attachment_type: str) -> tuple[bytes, str]:
    token = get_secret_value("ALLINO_ROCKETCHAT_TOKEN")
    user_id = get_secret_value("ALLINO_ROCKETCHAT_USER_ID")
    base_url = (os.getenv("ALLINO_ROCKETCHAT_BASE_URL") or "").rstrip("/")
    if not token or not user_id or not base_url:
        raise HTTPException(status_code=503, detail="Rocket.Chat is not configured")

    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        resp = client.get(
            f"{base_url}/file-upload/{attachment_ref}/file",
            headers={
                "X-Auth-Token": token,
                "X-User-Id": user_id,
                "User-Agent": "allino-backend",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch attachment from Rocket.Chat")
    if len(resp.content) > _MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="Attachment too large to display")

    default_media_type = {"image": "image/jpeg", "video": "video/mp4"}.get(attachment_type, "application/octet-stream")
    media_type = resp.headers.get("content-type") or default_media_type
    return resp.content, media_type


_ATTACHMENT_FETCHERS = {
    "rocketchat": _fetch_rocketchat_attachment,
}

# Rocket.Chat's own filename, dropped straight into a Content-Disposition header --
# strip anything that could break out of the quoted-string (quotes) or inject
# extra header lines (CR/LF), rather than trusting an external server's string.
_UNSAFE_FILENAME_CHARS = re.compile(r'["\r\n]')


def _sanitize_filename(name: str) -> str:
    return _UNSAFE_FILENAME_CHARS.sub("_", name)[:255]


@router.get("/messages/{event_id}/attachment")
def get_message_attachment(
    event_id: str,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> Response:
    """Proxies a message's image/video attachment through the backend, which holds
    the source's credentials -- the browser never receives (or needs) them. Only
    called when the user explicitly clicks "show image/video", never during sync,
    so opening a message never itself reveals to the source server that its media
    was viewed unless the user asks for it."""
    message = get_message(tenant_id=tenant_id, event_id=event_id)
    if message is None or not message.attachment_ref or not message.attachment_type:
        raise HTTPException(status_code=404, detail="No attachment for this message")

    fetcher = _ATTACHMENT_FETCHERS.get(message.source)
    if fetcher is None:
        raise HTTPException(status_code=501, detail=f"Attachments not supported for source '{message.source}'")

    content, media_type = fetcher(message.attachment_ref, message.attachment_type)
    headers = {}
    if message.attachment_type == "file" and message.attachment_name:
        headers["Content-Disposition"] = f'attachment; filename="{_sanitize_filename(message.attachment_name)}"'
    return Response(content=content, media_type=media_type, headers=headers)
