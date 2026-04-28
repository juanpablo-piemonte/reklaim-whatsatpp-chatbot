import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppClient:
    def send_text(self, to: str, text: str) -> dict:
        url = f"{_GRAPH_API_BASE}/{settings.whatsapp_phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text, "preview_url": False},
        }

        logger.info("[WhatsApp] → %s: %r", to, text)

        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            )

        logger.info("[WhatsApp] response %d: %s", response.status_code, response.text)

        if not response.is_success:
            logger.error("[WhatsApp] API error %d: %s", response.status_code, response.text)
            response.raise_for_status()

        data = response.json()
        message_id = (data.get("messages") or [{}])[0].get("id", "unknown")
        logger.info("[WhatsApp] sent OK message_id=%s", message_id)
        return data


whatsapp_client = WhatsAppClient()
