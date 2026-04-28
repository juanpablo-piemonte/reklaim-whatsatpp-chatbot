import json
import logging

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.core.security import verify_hmac

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
async def receive_message(request: Request):
    """Receive incoming WhatsApp messages from Meta."""
    from app.worker.tasks import process_whatsapp_message

    body_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_hmac(body_bytes, signature, settings.whatsapp_app_secret):
        logger.warning("WhatsApp webhook HMAC verification failed.")
        return Response(status_code=401)

    payload = json.loads(body_bytes)

    try:
        messages = payload["entry"][0]["changes"][0]["value"]["messages"]
    except (KeyError, IndexError, TypeError):
        logger.debug("Webhook payload contained no messages.")
        return {"status": "ok"}

    for message in messages:
        if message.get("type") != "text":
            continue
        wamid = message.get("id")
        body = message.get("text", {}).get("body", "")
        logger.info("Received message wamid=%s body=%r", wamid, body)
        process_whatsapp_message.delay(message)

    return {"status": "ok"}
