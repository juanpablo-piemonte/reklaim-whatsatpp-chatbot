import hashlib
import hmac
import json

SAMPLE_TEXT_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123456789",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550001234",
                            "phone_number_id": "987654321",
                        },
                        "contacts": [
                            {"profile": {"name": "Test User"}, "wa_id": "15559876543"}
                        ],
                        "messages": [
                            {
                                "from": "15559876543",
                                "id": "wamid.abc123",
                                "timestamp": "1700000000",
                                "type": "text",
                                "text": {"body": "Hello, I need help with my car."},
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}

SAMPLE_IMAGE_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123456789",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550001234",
                            "phone_number_id": "987654321",
                        },
                        "contacts": [
                            {"profile": {"name": "Test User"}, "wa_id": "15559876543"}
                        ],
                        "messages": [
                            {
                                "from": "15559876543",
                                "id": "wamid.img001",
                                "timestamp": "1700000001",
                                "type": "image",
                                "image": {
                                    "id": "media123",
                                    "mime_type": "image/jpeg",
                                    "caption": "Check this out",
                                },
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}

SAMPLE_STATUS_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123456789",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550001234",
                            "phone_number_id": "987654321",
                        },
                        "statuses": [
                            {
                                "id": "wamid.out001",
                                "status": "delivered",
                                "timestamp": "1700000002",
                                "recipient_id": "15559876543",
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}


def _sign(payload: dict, secret: str = "dev-secret") -> tuple[bytes, str]:
    """Return (body_bytes, sha256=... header value) for a payload."""
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return body, sig


# ── Health ────────────────────────────────────────────────────────────────────

async def test_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body.get("db") in (None, "connected", "unreachable", "not_configured")


# ── GET /webhooks/whatsapp — Meta hub verification ────────────────────────────

async def test_webhook_verification_valid(async_client):
    response = await async_client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "dev-verify-token",
            "hub.challenge": "challenge_abc",
        },
    )
    assert response.status_code == 200
    assert response.text == "challenge_abc"


async def test_webhook_verification_wrong_token(async_client):
    response = await async_client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "challenge_abc",
        },
    )
    assert response.status_code == 403


# ── POST /webhooks/whatsapp — HMAC ────────────────────────────────────────────

async def test_webhook_invalid_hmac(async_client):
    body = json.dumps(SAMPLE_TEXT_PAYLOAD).encode()
    response = await async_client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": "sha256=badhash", "Content-Type": "application/json"},
    )
    assert response.status_code == 401


async def test_webhook_missing_signature_returns_401(async_client):
    body = json.dumps(SAMPLE_TEXT_PAYLOAD).encode()
    response = await async_client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 401


# ── POST /webhooks/whatsapp — event dispatching ───────────────────────────────

async def test_webhook_text_message_enqueues_handler(async_client, mock_handlers):
    body, sig = _sign(SAMPLE_TEXT_PAYLOAD)
    response = await async_client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_handlers["message"].assert_called_once()


async def test_webhook_image_message_enqueues_handler(async_client, mock_handlers):
    body, sig = _sign(SAMPLE_IMAGE_PAYLOAD)
    response = await async_client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    mock_handlers["message"].assert_called_once()


async def test_webhook_status_update_enqueues_handler(async_client, mock_handlers):
    body, sig = _sign(SAMPLE_STATUS_PAYLOAD)
    response = await async_client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    mock_handlers["status"].assert_called_once()


async def test_webhook_empty_payload_returns_ok(async_client, mock_handlers):
    payload = {"object": "whatsapp_business_account", "entry": []}
    body, sig = _sign(payload)
    response = await async_client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    mock_handlers["message"].assert_not_called()
    mock_handlers["status"].assert_not_called()
