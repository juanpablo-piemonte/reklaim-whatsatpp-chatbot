from langchain_core.messages import HumanMessage

from app.whatsapp.models import AnyOutboundMessage, Contact, InboundMessage, OutboundText


def to_agent_input(message: InboundMessage, contact: Contact | None) -> dict:
    """Convert an inbound WhatsApp message into a LangGraph invoke payload."""
    contact_name = contact.profile.name if contact else None

    if message.type == "text":
        content = message.text.body if message.text else ""
        human_msg = HumanMessage(content=content)
    elif message.type == "image":
        image = message.image
        parts: list = []
        if image:
            # Pass image as a URL reference; get_media_url() must be called before this
            # and the resolved URL stored in image's context by the handler
            if hasattr(image, "_resolved_url") and image._resolved_url:
                parts.append({"type": "image_url", "image_url": {"url": image._resolved_url}})
            if image.caption:
                parts.append({"type": "text", "text": image.caption})
        human_msg = HumanMessage(content=parts or "")
    else:
        human_msg = HumanMessage(content=f"[{message.type} message]")

    return {
        "messages": [human_msg],
        "from_phone": message.from_,
        "stage": "greeting",
        "metadata": {"contact_name": contact_name},
    }


def extract_usage(result: dict) -> dict:
    """Extract token usage from the last AI message in the graph result."""
    last_msg = result.get("messages", [None])[-1]
    usage = getattr(last_msg, "usage_metadata", None) or {}
    return {
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_read_tokens": usage.get("cache_read_input_tokens"),
        "cache_write_tokens": usage.get("cache_creation_input_tokens"),
    }


def to_outbound_message(result: dict, to: str) -> AnyOutboundMessage:
    """Build an outbound WhatsApp message from the agent's graph result."""
    last_msg = result.get("messages", [None])[-1]
    text = getattr(last_msg, "content", "") or ""
    return OutboundText(to=to, body=text)
