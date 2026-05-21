import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class MonolithClient:
    """HTTP client for service-to-service calls back into the Rails monolith."""

    _TIMEOUT_SECONDS = 5.0

    def get_open_purchase_orders(self, from_phone: str) -> list:
        # Stub — the agent's tool layer will replace this once the monolith
        # exposes a real endpoint. Kept here so existing call sites don't break.
        logger.info("[Monolith STUB] get_open_purchase_orders for %s", from_phone)
        return [{"id": 1, "sku": "LUX-001", "quantity": 10, "target_price": 500.0}]

    def create_offer(self, data: dict) -> dict:
        logger.info("[Monolith STUB] create_offer %s", data)
        return {"offer_id": 999, "status": "pending_review"}

    def notify_dealer_message_during_takeover(
        self,
        conversation_id: int,
        wamid: str,
        body_preview: str,
    ) -> None:
        """Tell Rails an inbound dealer message arrived while a reviewer holds takeover.

        Rails fans the notification out to the reviewer (email today). We
        treat any failure as recoverable — losing one notification is a
        better failure mode than dropping an inbound message because the
        monolith is unreachable, so this method logs and swallows errors
        rather than re-raising.
        """
        if not settings.reklaim_api_url:
            logger.warning(
                "[MonolithClient] REKLAIM_API_URL not set; skipping dealer_message notify "
                "conversation=%s wamid=%s",
                conversation_id, wamid,
            )
            return
        if not settings.reklaim_internal_token:
            logger.warning(
                "[MonolithClient] REKLAIM_INTERNAL_TOKEN not set; skipping dealer_message notify "
                "conversation=%s wamid=%s",
                conversation_id, wamid,
            )
            return

        url = (
            f"{settings.reklaim_api_url.rstrip('/')}"
            f"/internal/conversations/{conversation_id}/dealer_message"
        )
        payload = {"wamid": wamid, "body_preview": body_preview}
        headers = {
            "X-Internal-Token": settings.reklaim_internal_token,
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=self._TIMEOUT_SECONDS)
        except httpx.HTTPError as exc:
            logger.warning(
                "[MonolithClient] dealer_message notify transport error conversation=%s: %s",
                conversation_id, exc,
            )
            return

        if response.status_code >= 400:
            logger.warning(
                "[MonolithClient] dealer_message notify non-2xx conversation=%s status=%s body=%s",
                conversation_id, response.status_code, response.text[:300],
            )


monolith_client = MonolithClient()
