import logging

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        from app.agent.graph import build_graph
        _graph = build_graph()
    return _graph


async def process_whatsapp_message(message: dict) -> str:
    from app.services.whatsapp_client import whatsapp_client

    dealer_phone: str = message.get("from", "unknown")
    text: str = message.get("text", {}).get("body", "")

    logger.info("[task] ← from=%s text=%r", dealer_phone, text)

    result = _get_graph().invoke(
        {
            "messages": [HumanMessage(content=text)],
            "dealer_phone": dealer_phone,
            "stage": "greeting",
            "metadata": {},
        },
        config={"configurable": {"thread_id": dealer_phone}},
    )

    response_text: str = getattr(result["messages"][-1], "content", "")

    logger.info("[task] → to=%s response=%r", dealer_phone, response_text)
    whatsapp_client.send_text(dealer_phone, response_text)
    return response_text
