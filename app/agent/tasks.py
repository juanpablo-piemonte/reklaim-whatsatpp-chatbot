import logging

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


async def process_whatsapp_message(message: dict) -> str:
    from app.agent.graph import get_graph
    from app.services.whatsapp_client import whatsapp_client

    dealer_phone: str = message.get("from", "unknown")
    text: str = message.get("text", {}).get("body", "")

    logger.info("[task] ← from=%s text=%r", dealer_phone, text)

    result = get_graph().invoke(
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
