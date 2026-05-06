import logging
import time

from app.core.chatbot.mapper import extract_usage, to_agent_input, to_outbound_message
from app.core.chatbot.session import get_or_create_conversation
from app.core.config import settings
from app.whatsapp.models import Contact, InboundMessage, PhoneMetadata, StatusUpdate
from app.whatsapp.parser import MessageEvent, StatusEvent

logger = logging.getLogger(__name__)


async def handle_message_event(event: MessageEvent) -> None:
    if event.message.type == "image":
        await _handle_inbound_image(event.message, event.contact, event.metadata)
    else:
        await _handle_inbound_text(event.message, event.contact, event.metadata)


async def handle_status_event(event: StatusEvent) -> None:
    await _handle_status_update(event.status, event.metadata)


async def _handle_inbound_text(
    message: InboundMessage,
    contact: Contact | None,
    metadata: PhoneMetadata,
) -> None:
    from_phone = message.from_
    logger.info("[handler] inbound text from=%s wamid=%s", from_phone, message.id)

    conv, db = get_or_create_conversation(metadata.phone_number_id, from_phone, contact)

    if db:
        from app.core.db.repositories import message_repo
        inbound_msg = message_repo.create(
            db,
            conversation_id=conv.id,
            wamid=message.id,
            message_type="text",
            direction="inbound",
            body=message.text.body if message.text else "",
            raw_payload=message.model_dump(by_alias=True),
        )
        if inbound_msg is None:
            logger.info("[handler] duplicate wamid=%s — skipping", message.id)
            return

    agent_input = to_agent_input(message, contact)
    result, latency_ms, error = _invoke_agent(from_phone, agent_input)

    if db:
        _persist_agent_run(db, conv.id, message.id, latency_ms, result, error)

    if error:
        logger.error("[handler] agent error for wamid=%s: %s", message.id, error)
        return

    from app.whatsapp.client import whatsapp_client
    outbound = to_outbound_message(result, to=from_phone)
    send_result = whatsapp_client.send(outbound)

    if db and send_result.wamid:
        from app.core.db.repositories import message_repo
        message_repo.create(
            db,
            conversation_id=conv.id,
            wamid=send_result.wamid,
            message_type=outbound.type,
            direction="outbound",
            body=getattr(outbound, "body", None),
            media_url=getattr(outbound, "media_url", None),
        )


async def _handle_inbound_image(
    message: InboundMessage,
    contact: Contact | None,
    metadata: PhoneMetadata,
) -> None:
    from_phone = message.from_
    image = message.image
    logger.info("[handler] inbound image from=%s wamid=%s", from_phone, message.id)

    conv, db = get_or_create_conversation(metadata.phone_number_id, from_phone, contact)

    media_url: str | None = None
    if image:
        try:
            from app.whatsapp.client import whatsapp_client
            media_url = whatsapp_client.get_media_url(image.id)
            object.__setattr__(image, "_resolved_url", media_url)
        except Exception as exc:
            logger.warning("[handler] could not resolve media URL: %s", exc)

    if db:
        from app.core.db.repositories import message_repo
        inbound_msg = message_repo.create(
            db,
            conversation_id=conv.id,
            wamid=message.id,
            message_type="image",
            direction="inbound",
            media_id=image.id if image else None,
            media_url=media_url,
            mime_type=image.mime_type if image else None,
            raw_payload=message.model_dump(by_alias=True),
        )
        if inbound_msg is None:
            logger.info("[handler] duplicate wamid=%s — skipping", message.id)
            return

    agent_input = to_agent_input(message, contact)
    result, latency_ms, error = _invoke_agent(from_phone, agent_input)

    if db:
        _persist_agent_run(db, conv.id, message.id, latency_ms, result, error)

    if error:
        logger.error("[handler] agent error for wamid=%s: %s", message.id, error)
        return

    from app.whatsapp.client import whatsapp_client
    outbound = to_outbound_message(result, to=from_phone)
    send_result = whatsapp_client.send(outbound)

    if db and send_result.wamid:
        from app.core.db.repositories import message_repo
        message_repo.create(
            db,
            conversation_id=conv.id,
            wamid=send_result.wamid,
            message_type=outbound.type,
            direction="outbound",
            body=getattr(outbound, "body", None),
        )


async def _handle_status_update(status: StatusUpdate, metadata: PhoneMetadata) -> None:
    logger.info("[handler] status wamid=%s status=%s", status.id, status.status)
    try:
        from app.core.db.engine import get_db
        from app.core.db.repositories import message_repo
        db = next(get_db())
        message_repo.update_status(db, status.id, status.status, status.timestamp)
    except RuntimeError:
        pass
    except Exception as exc:
        logger.warning("[handler] DB error updating status: %s", exc)


def _invoke_agent(from_phone: str, agent_input: dict) -> tuple[dict, int, str | None]:
    from app.agent.graph import get_graph
    t0 = time.monotonic()
    error: str | None = None
    result: dict = {}
    try:
        result = get_graph().invoke(
            agent_input,
            config={"configurable": {"thread_id": from_phone}},
        )
    except Exception as exc:
        error = str(exc)
        logger.exception("[handler] agent invocation failed: %s", exc)
    latency_ms = int((time.monotonic() - t0) * 1000)
    return result, latency_ms, error


def _persist_agent_run(db, conversation_id: int, wamid: str, latency_ms: int, result: dict, error: str | None) -> None:
    try:
        from app.core.db.repositories import agent_run_repo
        usage = extract_usage(result)
        agent_run_repo.create(
            db,
            conversation_id=conversation_id,
            triggered_by_wamid=wamid,
            model_id=settings.bedrock_model_id,
            latency_ms=latency_ms,
            error=error,
            **usage,
        )
    except Exception as exc:
        logger.warning("[handler] failed to persist agent run: %s", exc)
