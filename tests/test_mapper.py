from langchain_core.messages import AIMessage

from app.core.chatbot.mapper import (
    extract_thinking,
    extract_usage,
    to_agent_input,
    to_outbound_message,
)
from app.whatsapp.models import Contact, ContactProfile, ImageContent, InboundMessage, OutboundText


def _text_message(body: str = "Hello", from_: str = "5491234567890") -> InboundMessage:
    return InboundMessage.model_validate({
        "type": "text", "id": "wamid.test", "from": from_,
        "timestamp": "1700000000", "text": {"body": body},
    })


def _image_message(caption: str | None = None) -> InboundMessage:
    return InboundMessage.model_validate({
        "type": "image", "id": "wamid.img", "from": "5491234567890",
        "timestamp": "1700000000",
        "image": {"id": "media123", "mime_type": "image/jpeg", "caption": caption},
    })


def _contact(name: str = "Test User") -> Contact:
    return Contact(profile=ContactProfile(name=name), wa_id="5491234567890")


# ── extract_thinking ──────────────────────────────────────────────────────────

def test_extract_thinking_strips_block():
    clean, thinking = extract_thinking("<thinking>internal</thinking>\nActual response")
    assert clean == "Actual response"
    assert "internal" in thinking


def test_extract_thinking_absent_returns_none():
    clean, thinking = extract_thinking("Normal response")
    assert clean == "Normal response"
    assert thinking is None


def test_extract_thinking_case_insensitive():
    clean, _ = extract_thinking("<THINKING>thoughts</THINKING> Answer")
    assert clean == "Answer"


def test_extract_thinking_multiline():
    raw = "<thinking>\nline 1\nline 2\n</thinking>\nFinal answer"
    clean, thinking = extract_thinking(raw)
    assert clean == "Final answer"
    assert "line 1" in thinking


def test_extract_thinking_only_block_leaves_empty_clean():
    clean, thinking = extract_thinking("<thinking>only thinking</thinking>")
    assert clean == ""
    assert thinking is not None


# ── to_agent_input ────────────────────────────────────────────────────────────

def test_to_agent_input_text_message():
    result = to_agent_input(_text_message("What watches do you have?"), _contact())
    assert result["from_phone"] == "5491234567890"
    assert result["metadata"]["contact_name"] == "Test User"
    msgs = result["messages"]
    assert len(msgs) == 1
    assert msgs[0].content == "What watches do you have?"


def test_to_agent_input_no_contact():
    result = to_agent_input(_text_message(), None)
    assert result["metadata"]["contact_name"] is None


def test_to_agent_input_image_with_resolved_url():
    msg = _image_message(caption="Check this")
    object.__setattr__(msg.image, "_resolved_url", "https://cdn.example.com/img.jpg")
    result = to_agent_input(msg, None)
    content = result["messages"][0].content
    assert isinstance(content, list)
    types = [p["type"] for p in content]
    assert "image_url" in types
    assert "text" in types


def test_to_agent_input_image_without_resolved_url():
    msg = _image_message()
    result = to_agent_input(msg, None)
    # no resolved URL → content is empty string or empty list (no crash)
    content = result["messages"][0].content
    assert content == "" or content == []


def test_to_agent_input_unknown_type():
    msg = InboundMessage.model_validate({
        "type": "audio", "id": "wamid.x", "from": "5491234567890", "timestamp": "1700000000",
    })
    result = to_agent_input(msg, None)
    assert "[audio message]" in result["messages"][0].content


# ── extract_usage ─────────────────────────────────────────────────────────────

def test_extract_usage_with_metadata():
    msg = AIMessage(content="hi", usage_metadata={
        "input_tokens": 10, "output_tokens": 5, "total_tokens": 15,
        "cache_read_input_tokens": 2, "cache_creation_input_tokens": 1,
    })
    usage = extract_usage({"messages": [msg]})
    assert usage["input_tokens"] == 10
    assert usage["output_tokens"] == 5
    assert usage["cache_read_tokens"] == 2
    assert usage["cache_write_tokens"] == 1


def test_extract_usage_no_metadata():
    msg = AIMessage(content="hi")
    usage = extract_usage({"messages": [msg]})
    assert all(v is None for v in usage.values())


def test_extract_usage_empty_result():
    usage = extract_usage({})
    assert all(v is None for v in usage.values())


# ── to_outbound_message ───────────────────────────────────────────────────────

def test_to_outbound_text_message():
    msg = AIMessage(content="Here is what we have.")
    outbound, thinking = to_outbound_message({"messages": [msg]}, to="5491234567890")
    assert isinstance(outbound, OutboundText)
    assert outbound.body == "Here is what we have."
    assert outbound.to == "5491234567890"
    assert thinking is None


def test_to_outbound_strips_thinking_block():
    msg = AIMessage(content="<thinking>reasoning</thinking>\nClean reply")
    outbound, thinking = to_outbound_message({"messages": [msg]}, to="5491234567890")
    assert outbound.body == "Clean reply"
    assert thinking is not None
    assert "reasoning" in thinking
