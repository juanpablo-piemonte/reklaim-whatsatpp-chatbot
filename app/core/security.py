import hashlib
import hmac

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def require_api_key(api_key: str = Security(_api_key_header)) -> None:
    from app.core.config import settings
    if not hmac.compare_digest(api_key, settings.dealers_chatbot_api_key):
        raise HTTPException(status_code=403, detail="Forbidden")


def verify_hmac(payload: bytes, signature: str, secret: str) -> bool:
    """Verify a Meta webhook HMAC-SHA256 signature.

    signature is the raw X-Hub-Signature-256 header value, e.g. 'sha256=abcdef...'.
    Returns True if valid, False otherwise.
    """
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    provided = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)
