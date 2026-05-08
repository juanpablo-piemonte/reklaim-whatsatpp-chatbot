from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.core.chatbot.handlers import handle_message_event, handle_status_event
from app.whatsapp.models import OutboundText, SendResult
from app.whatsapp.parser import MessageEvent, StatusEvent


def _make_message_event(type_: str = "text", body: str = "Hi", wamid: str = "wamid.test"):
    from app.whatsapp.models import Contact, ContactProfile, InboundMessage, PhoneMetadata
    msg = InboundMessage.model_validate({
        "type": type_, "id": wamid, "from": "5491234567890", "timestamp": "1700000000",
        **({"text": {"body": body}} if type_ == "text" else
           {"image": {"id": "media123", "mime_type": "image/jpeg"}}),
    })
    contact = Contact(profile=ContactProfile(name="Test User"), wa_id="5491234567890")
    metadata = PhoneMetadata(display_phone_number="15550001234", phone_number_id="987")
    return MessageEvent(message=msg, contact=contact, metadata=metadata)


def _make_status_event(status: str = "delivered", wamid: str = "wamid.out"):
    from app.whatsapp.models import PhoneMetadata, StatusUpdate
    su = StatusUpdate(id=wamid, status=status, timestamp="1700000002", recipient_id="5491234567890")
    metadata = PhoneMetadata(display_phone_number="15550001234", phone_number_id="987")
    return StatusEvent(status=su, metadata=metadata)


def _mock_client(send_wamid: str = "wamid.reply"):
    client = MagicMock()
    client.mark_as_read = MagicMock()
    client.send.return_value = SendResult.model_validate({
        "messaging_product": "whatsapp",
        "messages": [{"id": send_wamid}],
    })
    return client


def _agent_result(content: str = "Agent reply") -> dict:
    return {"messages": [AIMessage(content=content)]}


# ── Text message handler ──────────────────────────────────────────────────────

async def test_handle_text_calls_mark_as_read():
    event = _make_message_event()
    client = _mock_client()
    with patch("app.core.chatbot.handlers.get_or_create_conversation", return_value=(None, None)), \
         patch("app.core.chatbot.handlers._invoke_agent", return_value=(_agent_result(), 100, None)), \
         patch("app.whatsapp.client.whatsapp_client", client):
        await handle_message_event(event)
    client.mark_as_read.assert_called_once_with("wamid.test")


async def test_handle_text_sends_agent_reply():
    event = _make_message_event()
    client = _mock_client()
    with patch("app.core.chatbot.handlers.get_or_create_conversation", return_value=(None, None)), \
         patch("app.core.chatbot.handlers._invoke_agent", return_value=(_agent_result("Hello!"), 100, None)), \
         patch("app.whatsapp.client.whatsapp_client", client):
        await handle_message_event(event)
    client.send.assert_called_once()
    sent: OutboundText = client.send.call_args[0][0]
    assert sent.body == "Hello!"
    assert sent.to == "5491234567890"


async def test_handle_text_agent_error_sends_fallback():
    event = _make_message_event()
    client = _mock_client()
    with patch("app.core.chatbot.handlers.get_or_create_conversation", return_value=(None, None)), \
         patch("app.core.chatbot.handlers._invoke_agent", return_value=({}, 50, "Bedrock timeout")), \
         patch("app.whatsapp.client.whatsapp_client", client):
        await handle_message_event(event)
    client.send.assert_called_once()
    sent: OutboundText = client.send.call_args[0][0]
    assert "issue" in sent.body.lower() or "problema" in sent.body.lower()


async def test_handle_text_no_db_still_invokes_agent():
    event = _make_message_event()
    client = _mock_client()
    invoke_mock = MagicMock(return_value=(_agent_result(), 100, None))
    with patch("app.core.chatbot.handlers.get_or_create_conversation", return_value=(None, None)), \
         patch("app.core.chatbot.handlers._invoke_agent", invoke_mock), \
         patch("app.whatsapp.client.whatsapp_client", client):
        await handle_message_event(event)
    invoke_mock.assert_called_once()
    client.send.assert_called_once()


async def test_handle_text_send_failure_does_not_raise():
    event = _make_message_event()
    client = _mock_client()
    client.send.side_effect = Exception("Meta API down")
    with patch("app.core.chatbot.handlers.get_or_create_conversation", return_value=(None, None)), \
         patch("app.core.chatbot.handlers._invoke_agent", return_value=(_agent_result(), 100, None)), \
         patch("app.whatsapp.client.whatsapp_client", client):
        await handle_message_event(event)  # must not raise


# ── Image message handler ─────────────────────────────────────────────────────

async def test_handle_image_calls_mark_as_read():
    event = _make_message_event(type_="image", wamid="wamid.img")
    client = _mock_client()
    client.get_media_url = MagicMock(return_value="https://cdn.example.com/img.jpg")
    with patch("app.core.chatbot.handlers.get_or_create_conversation", return_value=(None, None)), \
         patch("app.core.chatbot.handlers._invoke_agent", return_value=(_agent_result(), 100, None)), \
         patch("app.whatsapp.client.whatsapp_client", client):
        await handle_message_event(event)
    client.mark_as_read.assert_called_once_with("wamid.img")


async def test_handle_image_media_url_failure_continues():
    event = _make_message_event(type_="image")
    client = _mock_client()
    client.get_media_url = MagicMock(side_effect=Exception("Media API error"))
    with patch("app.core.chatbot.handlers.get_or_create_conversation", return_value=(None, None)), \
         patch("app.core.chatbot.handlers._invoke_agent", return_value=(_agent_result(), 100, None)), \
         patch("app.whatsapp.client.whatsapp_client", client):
        await handle_message_event(event)  # must not raise
    client.send.assert_called_once()


# ── Status handler ────────────────────────────────────────────────────────────

async def test_handle_status_no_db_does_not_raise():
    event = _make_status_event()
    with patch("app.core.db.engine.get_db", side_effect=RuntimeError("no db")):
        await handle_status_event(event)  # must not raise


async def test_handle_status_db_error_does_not_raise():
    event = _make_status_event()
    with patch("app.core.db.engine.get_db", side_effect=Exception("connection error")):
        await handle_status_event(event)  # must not raise
