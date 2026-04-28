import logging

from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.agent.graph import build_graph

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatTestRequest(BaseModel):
    phone: str
    message: str


@router.post("/test")
def chat_test(body: ChatTestRequest) -> dict:
    """Directly invoke the agent and return the response as JSON.
    Use this to test the Bedrock integration without needing WhatsApp.
    FastAPI runs sync routes in a thread pool so graph.invoke() won't block the event loop.
    """
    logger.info("[/chat/test] phone=%s message=%r", body.phone, body.message)

    graph = build_graph()
    result = graph.invoke(
        {
            "messages": [HumanMessage(content=body.message)],
            "dealer_phone": body.phone,
            "stage": "greeting",
            "metadata": {},
        },
        config={"configurable": {"thread_id": body.phone}},
    )

    response_text: str = getattr(result["messages"][-1], "content", "")
    logger.info("[/chat/test] response=%r", response_text)
    return {"response": response_text, "phone": body.phone}
