import hashlib
import hmac


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
