from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.whatsapp.models import SendResult


TOKEN = "test-internal-token"


def _send_result(wamid: str) -> SendResult:
    # SendResult.wamid is a computed property reading messages[0]["id"];
    # construct it with the proper shape rather than passing wamid as a kwarg.
    return SendResult.model_validate({
        "messaging_product": "whatsapp",
        "messages": [{"id": wamid}],
    })


@pytest.fixture(autouse=True)
def patch_internal_token():
    with patch.object(settings, "chatbot_internal_token", TOKEN), \
         patch.object(settings, "whatsapp_phone_number_id", "test-phone-num-id"):
        yield


@pytest.fixture
def mock_whatsapp_send():
    fake = _send_result("wamid.LOCAL-TEST-001")
    with patch("app.core.api.internal.whatsapp_client") as wa:
        wa.send.return_value = fake
        yield wa


@pytest.fixture
def mock_db():
    fake_conv = MagicMock(id=7, from_phone="+15551112222")
    fake_msg  = MagicMock(id=42, wamid="wamid.LOCAL-TEST-001")
    with patch("app.core.api.internal.conversation_repo") as conv_repo, \
         patch("app.core.api.internal.message_repo") as msg_repo, \
         patch("app.core.api.internal.get_db") as get_db:
        conv_repo.get_or_create.return_value = fake_conv
        conv_repo.get_by_id.return_value     = fake_conv
        msg_repo.create.return_value         = fake_msg
        msg_repo.find_by_idempotency_key.return_value = None
        get_db.return_value = iter([MagicMock()])
        yield {"conv_repo": conv_repo, "msg_repo": msg_repo}


HEADERS_OK = {"X-Internal-Token": TOKEN, "Content-Type": "application/json"}


@pytest.mark.asyncio
async def test_returns_401_without_token(async_client):
    resp = await async_client.post("/internal/outbound", json={"body": "x", "sender": {"type": "reviewer", "reviewer_id": 1}, "conversation_id": 1})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_returns_401_with_bad_token(async_client):
    resp = await async_client.post("/internal/outbound", headers={"X-Internal-Token": "wrong"},
                                    json={"body": "x", "sender": {"type": "reviewer", "reviewer_id": 1}, "conversation_id": 1})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_returns_422_when_neither_conversation_id_nor_dealer_phone(async_client, mock_db, mock_whatsapp_send):
    resp = await async_client.post("/internal/outbound", headers=HEADERS_OK,
                                    json={"body": "x", "sender": {"type": "reviewer", "reviewer_id": 1}})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reviewer_reply_happy_path(async_client, mock_db, mock_whatsapp_send):
    resp = await async_client.post("/internal/outbound", headers=HEADERS_OK,
                                    json={"body": "thanks", "sender": {"type": "reviewer", "reviewer_id": 1}, "conversation_id": 7})
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"message_id": 42, "wamid": "wamid.LOCAL-TEST-001", "conversation_id": 7, "status": "sent"}
    mock_whatsapp_send.send.assert_called_once()
    mock_db["msg_repo"].create.assert_called_once()


@pytest.mark.asyncio
async def test_campaign_first_touch_creates_conversation(async_client, mock_db, mock_whatsapp_send):
    resp = await async_client.post("/internal/outbound", headers=HEADERS_OK,
                                    json={"body": "Hi!", "sender": {"type": "campaign", "campaign_id": 99}, "dealer_phone": "+15551112222"})
    assert resp.status_code == 200
    mock_db["conv_repo"].get_or_create.assert_called_once()
    kwargs = mock_db["conv_repo"].get_or_create.call_args.kwargs
    assert kwargs["campaign_id"] == 99, "sender.campaign_id must flow through to conversation row"


@pytest.mark.asyncio
async def test_campaign_first_touch_persists_dealer_id_when_provided(async_client, mock_db, mock_whatsapp_send):
    resp = await async_client.post("/internal/outbound", headers=HEADERS_OK,
                                    json={
                                        "body": "Hi!",
                                        "sender": {"type": "campaign", "campaign_id": 99},
                                        "dealer_phone": "+15551112222",
                                        "dealer_id": 42,
                                    })
    assert resp.status_code == 200
    kwargs = mock_db["conv_repo"].get_or_create.call_args.kwargs
    assert kwargs["dealer_id"] == 42
    assert kwargs["campaign_id"] == 99


@pytest.mark.asyncio
async def test_reviewer_reply_does_not_set_campaign_id_on_conversation(async_client, mock_db, mock_whatsapp_send):
    # Reviewer dispatch uses conversation_id, so get_by_id is used (not get_or_create).
    resp = await async_client.post("/internal/outbound", headers=HEADERS_OK,
                                    json={"body": "thanks", "sender": {"type": "reviewer", "reviewer_id": 1}, "conversation_id": 7})
    assert resp.status_code == 200
    mock_db["conv_repo"].get_or_create.assert_not_called()


@pytest.mark.asyncio
async def test_returns_502_on_meta_failure_and_does_not_persist(async_client, mock_db, mock_whatsapp_send):
    mock_whatsapp_send.send.side_effect = Exception("meta is down")
    resp = await async_client.post("/internal/outbound", headers=HEADERS_OK,
                                    json={"body": "x", "sender": {"type": "reviewer", "reviewer_id": 1}, "conversation_id": 7})
    assert resp.status_code == 502
    mock_db["msg_repo"].create.assert_not_called()


@pytest.mark.asyncio
async def test_idempotency_returns_existing_without_resend(async_client, mock_db, mock_whatsapp_send):
    existing = MagicMock(id=88, wamid="wamid.EXISTING")
    mock_db["msg_repo"].find_by_idempotency_key.return_value = existing
    resp = await async_client.post("/internal/outbound", headers=HEADERS_OK,
                                    json={"body": "x", "sender": {"type": "campaign", "campaign_id": 99}, "dealer_phone": "+15551112222", "idempotency_key": "abc"})
    assert resp.status_code == 200
    assert resp.json()["message_id"] == 88
    mock_whatsapp_send.send.assert_not_called()


@pytest.mark.asyncio
async def test_template_id_without_payload_warns_and_sends_as_text(async_client, mock_db, mock_whatsapp_send, caplog):
    import logging
    caplog.set_level(logging.WARNING)
    resp = await async_client.post("/internal/outbound", headers=HEADERS_OK,
                                    json={"body": "x", "sender": {"type": "campaign", "campaign_id": 99}, "dealer_phone": "+15551112222", "template_id": 5})
    assert resp.status_code == 200
    assert any("template_id" in rec.message for rec in caplog.records)
    mock_whatsapp_send.send.assert_called_once()
    from app.whatsapp.models import OutboundText
    sent = mock_whatsapp_send.send.call_args[0][0]
    assert isinstance(sent, OutboundText)


@pytest.mark.asyncio
async def test_template_payload_sends_as_template(async_client, mock_db, mock_whatsapp_send):
    from app.whatsapp.models import OutboundTemplate
    resp = await async_client.post("/internal/outbound", headers=HEADERS_OK,
                                    json={
                                        "body": "Hi {{1}}",  # fallback only; not used when template present
                                        "sender": {"type": "campaign", "campaign_id": 99},
                                        "dealer_phone": "+15551112222",
                                        "template_id": 5,
                                        "template": {
                                            "name": "hello_world",
                                            "language": "en_US",
                                            "components": [],
                                        },
                                    })
    assert resp.status_code == 200
    sent = mock_whatsapp_send.send.call_args[0][0]
    assert isinstance(sent, OutboundTemplate)
    assert sent.name == "hello_world"
    assert sent.language.code == "en_US"
    assert sent.components == []
    mock_db["msg_repo"].create.assert_called_once()
    assert mock_db["msg_repo"].create.call_args.kwargs["message_type"] == "template"


@pytest.mark.asyncio
async def test_template_with_body_parameters(async_client, mock_db, mock_whatsapp_send):
    from app.whatsapp.models import OutboundTemplate
    resp = await async_client.post("/internal/outbound", headers=HEADERS_OK,
                                    json={
                                        "body": "Hi Juanpi, looking for rolex submariner within $1k-$5k",
                                        "sender": {"type": "campaign", "campaign_id": 99},
                                        "dealer_phone": "+15551112222",
                                        "template_id": 5,
                                        "template": {
                                            "name": "campaign_dealer_intro_v1",
                                            "language": "en_US",
                                            "components": [
                                                {
                                                    "type": "body",
                                                    "parameters": [
                                                        {"type": "text", "text": "Juanpi"},
                                                        {"type": "text", "text": "rolex submariner"},
                                                        {"type": "text", "text": "$1k-$5k"},
                                                    ],
                                                }
                                            ],
                                        },
                                    })
    assert resp.status_code == 200
    sent = mock_whatsapp_send.send.call_args[0][0]
    assert isinstance(sent, OutboundTemplate)
    assert sent.name == "campaign_dealer_intro_v1"
    assert len(sent.components) == 1
    assert sent.components[0].type == "body"
    assert len(sent.components[0].parameters) == 3
    assert sent.components[0].parameters[1].text == "rolex submariner"
