import logging

import httpx

from app.core.config import settings
from app.whatsapp.models import AnyOutboundMessage, OutboundImage, OutboundText, SendResult

logger = logging.getLogger(__name__)

_META_API_VERSION = "v23.0"
_GRAPH_API_BASE = f"https://graph.facebook.com/{_META_API_VERSION}"


class WhatsAppClient:
    def send(self, msg: AnyOutboundMessage) -> SendResult:
        if isinstance(msg, OutboundText):
            return self._send_text(msg)
        if isinstance(msg, OutboundImage):
            return self._send_image(msg)
        raise ValueError(f"Unsupported outbound message type: {type(msg)}")

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
        url = f"{_GRAPH_API_BASE}/{settings.whatsapp_phone_number_id}/messages"
        logger.info("[WhatsApp] → %s type=%s", to, payload.get("type"))
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
