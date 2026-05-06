import json
import logging

from fastapi import APIRouter, BackgroundTasks, Query, Request, Response
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.core.security import verify_hmac
from app.whatsapp.parser import MessageEvent, StatusEvent, parse_webhook_payload

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/whatsapp")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    verify_token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta webhook verification handshake."""
    if mode == "subscribe" and verify_token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified successfully.")
        return PlainTextResponse(content=challenge, status_code=200)
    logger.warning("WhatsApp webhook verification failed.")
    return Response(status_code=403)


@router.post("/whatsapp")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """Receive and dispatch incoming WhatsApp events from Meta."""
    from app.core.chatbot.handlers import handle_message_event, handle_status_event

    body_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_hmac(body_bytes, signature, settings.whatsapp_app_secret):
        logger.warning("WhatsApp webhook HMAC verification failed.")
        return Response(status_code=401)

    raw = json.loads(body_bytes)
    events = parse_webhook_payload(raw)

    for event in events:
        if isinstance(event, MessageEvent):
            background_tasks.add_task(handle_message_event, event)
        elif isinstance(event, StatusEvent):
            background_tasks.add_task(handle_status_event, event)

    return {"status": "ok"}
