import hashlib
import hmac
import json

import pytest

SAMPLE_META_PAYLOAD = {
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


def _sign(payload: dict, secret: str = "dev-secret") -> tuple[bytes, str]:
    """Return (body_bytes, sha256=... header value) for a payload."""
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return body, sig


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

async def test_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /webhooks/whatsapp — Meta hub verification
# ---------------------------------------------------------------------------

async def test_webhook_verification_valid(async_client):
    """Valid hub.verify_token returns 200 and echoes the challenge."""
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


# ---------------------------------------------------------------------------
# POST /webhooks/whatsapp — incoming messages
# ---------------------------------------------------------------------------

async def test_webhook_invalid_hmac(async_client):
    """Request with a bad HMAC signature is rejected with 401."""
    body = json.dumps(SAMPLE_META_PAYLOAD).encode()
    response = await async_client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={
            "X-Hub-Signature-256": "sha256=badhash",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 401


async def test_webhook_missing_signature_returns_401(async_client):
    body = json.dumps(SAMPLE_META_PAYLOAD).encode()
    response = await async_client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 401


async def test_webhook_valid_message(async_client, mock_celery_task):
    """Valid HMAC + text message → Celery task enqueued, 200 returned."""
    body, sig = _sign(SAMPLE_META_PAYLOAD)
    response = await async_client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_celery_task.assert_called_once()


async def test_webhook_no_messages_does_not_enqueue(async_client, mock_celery_task):
    payload = {"object": "whatsapp_business_account", "entry": []}
    body, sig = _sign(payload)
    response = await async_client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_celery_task.assert_not_called()


async def test_webhook_non_text_message_not_enqueued(async_client, mock_celery_task):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "15559876543",
                                    "id": "wamid.xyz999",
                                    "timestamp": "1700000001",
                                    "type": "image",
                                    "image": {"id": "img123"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    body, sig = _sign(payload)
    response = await async_client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    mock_celery_task.assert_not_called()
