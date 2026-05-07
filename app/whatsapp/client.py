import logging

import httpx

from app.core.config import settings
from app.whatsapp.models import AnyOutboundMessage, OutboundImage, OutboundText, SendResult

logger = logging.getLogger(__name__)

_META_API_VERSION = "v25.0"
_GRAPH_API_BASE = f"https://graph.facebook.com/{_META_API_VERSION}"


def _normalize_phone(number: str) -> str:
    """Normalize Argentine WhatsApp numbers for outbound sending.
    WhatsApp delivers inbound from=549AREA... but the API expects 54AREA15... to send back.
    """
    if number.startswith("549") and len(number) == 13:
        # 549 + 3-digit area + 7-digit local → 54 + area + 15 + local
        area = number[3:6]
        local = number[6:]
        return f"54{area}15{local}"
    return number


class WhatsAppClient:
    def send(self, msg: AnyOutboundMessage) -> SendResult:
        if isinstance(msg, OutboundText):
            return self._send_text(msg)
        if isinstance(msg, OutboundImage):
            return self._send_image(msg)
        raise ValueError(f"Unsupported outbound message type: {type(msg)}")

    def mark_as_read(self, wamid: str) -> None:
        """Send a read receipt for an inbound message."""
        url = f"{_GRAPH_API_BASE}/{settings.whatsapp_phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": wamid,
        }
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(
                    url,
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
                )
            if not resp.is_success:
                logger.warning("[WhatsApp] mark_as_read failed %d: %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.warning("[WhatsApp] mark_as_read error: %s", exc)

    def get_media_url(self, media_id: str) -> str:
        """Resolve a Meta media ID to its temporary download URL."""
        url = f"{_GRAPH_API_BASE}/{media_id}"
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                url,
                headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            )
        resp.raise_for_status()
        return resp.json()["url"]

    def _send_text(self, msg: OutboundText) -> SendResult:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": msg.to,
            "type": "text",
            "text": {"body": msg.body, "preview_url": msg.preview_url},
        }
        return self._post_message(msg.to, payload)

    def _send_image(self, msg: OutboundImage) -> SendResult:
        if not msg.media_id and not msg.media_url:
            raise ValueError("OutboundImage requires either media_id or media_url")
        image_payload: dict = {}
        if msg.media_id:
            image_payload["id"] = msg.media_id
        else:
            image_payload["link"] = msg.media_url
        if msg.caption:
            image_payload["caption"] = msg.caption
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": msg.to,
            "type": "image",
            "image": image_payload,
        }
        return self._post_message(msg.to, payload)

    def _post_message(self, to: str, payload: dict) -> SendResult:
        normalized = _normalize_phone(to)
        payload["to"] = normalized
        url = f"{_GRAPH_API_BASE}/{settings.whatsapp_phone_number_id}/messages"
        logger.info("[WhatsApp] → %s (normalized from %s) type=%s", normalized, to, payload.get("type"))
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            )
        logger.info("[WhatsApp] response %d", resp.status_code)
        if not resp.is_success:
            logger.error("[WhatsApp] API error %d: %s", resp.status_code, resp.text)
            resp.raise_for_status()
        result = SendResult.model_validate(resp.json())
        logger.info("[WhatsApp] sent OK wamid=%s", result.wamid)
        return result


whatsapp_client = WhatsAppClient()
