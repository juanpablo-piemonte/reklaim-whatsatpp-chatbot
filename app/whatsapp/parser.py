import logging
from dataclasses import dataclass

from app.whatsapp.models import Contact, InboundMessage, PhoneMetadata, StatusUpdate, WebhookPayload

logger = logging.getLogger(__name__)


@dataclass
class MessageEvent:
    message: InboundMessage
    contact: Contact | None
    metadata: PhoneMetadata


@dataclass
class StatusEvent:
    status: StatusUpdate
    metadata: PhoneMetadata


WebhookEvent = MessageEvent | StatusEvent


def parse_webhook_payload(raw: dict) -> list[WebhookEvent]:
    """Parse a raw Meta webhook payload into a flat list of typed events."""
    try:
        payload = WebhookPayload.model_validate(raw)
    except Exception as exc:
        logger.warning("Failed to parse webhook payload: %s", exc)
        return []

    events: list[WebhookEvent] = []

    for entry in payload.entry:
        for change in entry.changes:
            if change.field != "messages":
                continue
            value = change.value
            contacts_by_wa_id = {c.wa_id: c for c in value.contacts}

            for message in value.messages:
                contact = contacts_by_wa_id.get(message.from_)
                events.append(MessageEvent(
                    message=message,
                    contact=contact,
                    metadata=value.metadata,
                ))

            for status in value.statuses:
                events.append(StatusEvent(
                    status=status,
                    metadata=value.metadata,
                ))

    return events
