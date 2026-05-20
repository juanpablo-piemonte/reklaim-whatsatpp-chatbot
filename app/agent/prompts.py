import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHE: dict = {}        # { name: (fetched_at_monotonic, body) }
_CACHE_TTL_S = 300       # 5 minutes

# Fallback used only if Rails is unreachable AND no cache entry exists.
# Should mirror the seeded default in backend/db/seeds/dealers_chatbot.rb so
# behavior degrades gracefully rather than failing the agent boot.
_FALLBACK_PROMPT = """\
You are a helpful assistant for Reklaim, a luxury goods marketplace where dealers buy and sell high-end watches, jewelry, and accessories.

You have access to a tool that fetches live product data from Reklaim's inventory. Use it when the user asks to see a product, browse what's available, or wants real details about a listing. For everything else — greetings, questions about how Reklaim works, general conversation — answer directly without calling any tool.

When you do fetch a product, present the key details in a clean, readable format: name, condition, year, price (with currency), accessories included, and a note about available images. Always be concise and helpful.\
"""


def load_active_prompt(name: str = "default") -> str:
    """Fetch the active prompt body by name from Rails, with a 5-minute TTL cache."""
    cached = _CACHE.get(name)
    if cached and (time.monotonic() - cached[0]) < _CACHE_TTL_S:
        return cached[1]

    try:
        resp = httpx.get(
            f"{settings.reklaim_api_url}/dealers_chatbot/prompts/{name}",
            headers={"Authorization": f"Bearer {settings.dealers_chatbot_api_key}"},
            timeout=5.0,
        )
        resp.raise_for_status()
        body = resp.json()["body"]
        _CACHE[name] = (time.monotonic(), body)
        return body
    except Exception as exc:
        logger.warning("[prompts] fetch failed for %s, using cached/fallback: %s", name, exc)
        if cached:
            return cached[1]
        return _FALLBACK_PROMPT
