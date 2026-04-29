import json
import logging

import httpx
from langchain_core.tools import tool

from app.core.config import settings

logger = logging.getLogger(__name__)


@tool
def get_random_product() -> str:
    """Fetch a random product from Reklaim's live inventory and return its full details:
    brand, model, SKU, condition, year, price, currency, accessories, and image URLs.

    Use this tool when the user:
    - Asks to see a product or browse inventory
    - Wants to know what's available or what Reklaim sells
    - Asks about a specific product category, brand, or price range (fetch one to illustrate)
    - Requests an example of a listing

    Do NOT use this tool for greetings, general questions about Reklaim, or anything
    that doesn't require live product data.
    """
    headers = {"Authorization": f"Bearer {settings.dealers_chatbot_api_key}"}
    try:
        resp = httpx.get(
            f"{settings.reklaim_api_url}/dealers_chatbot/dealers/random_product",
            headers=headers,
            timeout=10.0,
        )
        resp.raise_for_status()
        product = resp.json()["product"]
        logger.info("[tool] get_random_product → sku=%s", product.get("sku"))
        return json.dumps(product, ensure_ascii=False)
    except httpx.HTTPStatusError as e:
        logger.error("[tool] get_random_product HTTP error %d", e.response.status_code)
        return f"Error fetching product: API returned {e.response.status_code}"
    except Exception as e:
        logger.error("[tool] get_random_product error: %s", e)
        return f"Error fetching product: {e}"
