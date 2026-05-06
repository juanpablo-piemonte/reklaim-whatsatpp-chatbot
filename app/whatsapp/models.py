from typing import Literal

from pydantic import BaseModel, Field


# ── Inbound: Meta webhook payload ────────────────────────────────────────────

class PhoneMetadata(BaseModel):
    display_phone_number: str
    phone_number_id: str


class ContactProfile(BaseModel):
    name: str


class Contact(BaseModel):
    profile: ContactProfile
    wa_id: str


class TextContent(BaseModel):
    body: str


class ImageContent(BaseModel):
    id: str
    mime_type: str | None = None
    sha256: str | None = None
    caption: str | None = None


class InboundMessage(BaseModel):
    """A single inbound message from a WhatsApp user.
    Type-specific content is in the `text` or `image` fields based on `type`."""
    type: str
    id: str
    from_: str = Field(alias="from")
    timestamp: str
    text: TextContent | None = None
    image: ImageContent | None = None

    model_config = {"populate_by_name": True}


class StatusUpdate(BaseModel):
    id: str  # wamid of the original outbound message
    status: Literal["sent", "delivered", "read", "failed"]
    timestamp: str
    recipient_id: str


class ChangeValue(BaseModel):
    messaging_product: str
    metadata: PhoneMetadata
    contacts: list[Contact] = []
    messages: list[InboundMessage] = []
    statuses: list[StatusUpdate] = []


class Change(BaseModel):
    value: ChangeValue
    field: str


class Entry(BaseModel):
    id: str
    changes: list[Change]


class WebhookPayload(BaseModel):
    object: str
    entry: list[Entry]


# ── Outbound: messages sent to WhatsApp users ─────────────────────────────────

class OutboundText(BaseModel):
    type: Literal["text"] = "text"
    to: str
    body: str
    preview_url: bool = False


class OutboundImage(BaseModel):
    type: Literal["image"] = "image"
    to: str
    media_id: str | None = None   # preferred: uploaded media ID
    media_url: str | None = None  # fallback: public URL
    caption: str | None = None


AnyOutboundMessage = OutboundText | OutboundImage


class SendResult(BaseModel):
    messaging_product: str
    contacts: list[dict] = []
    messages: list[dict] = []

    @property
    def wamid(self) -> str | None:
        return (self.messages or [{}])[0].get("id")
