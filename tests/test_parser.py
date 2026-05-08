from app.whatsapp.parser import MessageEvent, StatusEvent, parse_webhook_payload


def _base_value(**kwargs):
    return {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "15550001234", "phone_number_id": "987"},
        "contacts": [],
        "messages": [],
        "statuses": [],
        **kwargs,
    }


def _payload(*changes):
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "123", "changes": list(changes)}],
    }


def _msg_change(value: dict):
    return {"field": "messages", "value": value}


# ── Text messages ─────────────────────────────────────────────────────────────

def test_text_message_parsed():
    raw = _payload(_msg_change(_base_value(
        contacts=[{"profile": {"name": "Test User"}, "wa_id": "5491234567890"}],
        messages=[{
            "from": "5491234567890", "id": "wamid.abc", "timestamp": "1700000000",
            "type": "text", "text": {"body": "Hello"},
        }],
    )))
    events = parse_webhook_payload(raw)
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, MessageEvent)
    assert ev.message.type == "text"
    assert ev.message.text.body == "Hello"
    assert ev.message.from_ == "5491234567890"
    assert ev.contact.profile.name == "Test User"
    assert ev.metadata.phone_number_id == "987"


def test_message_without_contact_yields_none_contact():
    raw = _payload(_msg_change(_base_value(
        contacts=[],
        messages=[{
            "from": "5491234567890", "id": "wamid.abc", "timestamp": "1700000000",
            "type": "text", "text": {"body": "Hi"},
        }],
    )))
    events = parse_webhook_payload(raw)
    assert len(events) == 1
    assert events[0].contact is None


def test_contact_without_profile_field():
    raw = _payload(_msg_change(_base_value(
        contacts=[{"wa_id": "5491234567890"}],
        messages=[{
            "from": "5491234567890", "id": "wamid.abc", "timestamp": "1700000000",
            "type": "text", "text": {"body": "Hi"},
        }],
    )))
    events = parse_webhook_payload(raw)
    assert len(events) == 1
    assert events[0].contact.profile is None


# ── Image messages ────────────────────────────────────────────────────────────

def test_image_message_parsed():
    raw = _payload(_msg_change(_base_value(
        contacts=[{"profile": {"name": "Sender"}, "wa_id": "5491234567890"}],
        messages=[{
            "from": "5491234567890", "id": "wamid.img", "timestamp": "1700000001",
            "type": "image",
            "image": {"id": "media123", "mime_type": "image/jpeg", "caption": "Look at this"},
        }],
    )))
    events = parse_webhook_payload(raw)
    assert len(events) == 1
    ev = events[0]
    assert ev.message.type == "image"
    assert ev.message.image.id == "media123"
    assert ev.message.image.caption == "Look at this"


# ── Status updates ────────────────────────────────────────────────────────────

def test_status_update_parsed():
    raw = _payload(_msg_change(_base_value(
        statuses=[{
            "id": "wamid.out001", "status": "delivered",
            "timestamp": "1700000002", "recipient_id": "5491234567890",
        }],
    )))
    events = parse_webhook_payload(raw)
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, StatusEvent)
    assert ev.status.id == "wamid.out001"
    assert ev.status.status == "delivered"


# ── Multiple events ───────────────────────────────────────────────────────────

def test_multiple_events_in_one_payload():
    raw = _payload(_msg_change(_base_value(
        contacts=[{"profile": {"name": "A"}, "wa_id": "111"}, {"profile": {"name": "B"}, "wa_id": "222"}],
        messages=[
            {"from": "111", "id": "wamid.1", "timestamp": "1700000000", "type": "text", "text": {"body": "Msg1"}},
            {"from": "222", "id": "wamid.2", "timestamp": "1700000001", "type": "text", "text": {"body": "Msg2"}},
        ],
        statuses=[{
            "id": "wamid.out", "status": "read", "timestamp": "1700000002", "recipient_id": "111",
        }],
    )))
    events = parse_webhook_payload(raw)
    assert len(events) == 3
    assert sum(isinstance(e, MessageEvent) for e in events) == 2
    assert sum(isinstance(e, StatusEvent) for e in events) == 1


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_malformed_payload_returns_empty():
    assert parse_webhook_payload({"bad": "data"}) == []


def test_empty_entries_returns_empty():
    assert parse_webhook_payload({"object": "whatsapp_business_account", "entry": []}) == []


def test_non_messages_field_skipped():
    raw = _payload({"field": "account_alerts", "value": _base_value()})
    assert parse_webhook_payload(raw) == []
