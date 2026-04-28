import logging

logger = logging.getLogger(__name__)


class MonolithClient:
    def get_open_purchase_orders(self, dealer_phone: str) -> list:
        logger.info("[Monolith STUB] get_open_purchase_orders for %s", dealer_phone)
        return [{"id": 1, "sku": "LUX-001", "quantity": 10, "target_price": 500.0}]

    def create_offer(self, data: dict) -> dict:
        logger.info("[Monolith STUB] create_offer %s", data)
        return {"offer_id": 999, "status": "pending_review"}


monolith_client = MonolithClient()
