from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from app.agent.graph import build_graph
from app.core.api.main import app
from app.core.config import settings


@pytest.fixture(autouse=True)
def patch_settings():
    """Force test credential defaults regardless of .env content."""
    with patch.object(settings, "whatsapp_verify_token", "dev-verify-token"), \
         patch.object(settings, "whatsapp_app_secret", "dev-secret"):
        yield


@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_bedrock():
    """Patch ChatBedrock so tests never hit AWS."""
    fake = AIMessage(content="Mocked Bedrock response.")
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value.invoke.return_value = fake
    with patch("app.agent.graph.ChatBedrock", return_value=mock_llm):
        yield mock_llm


@pytest.fixture
def graph(mock_bedrock):
    """Compiled agent graph with MemorySaver and mocked Bedrock — no external services needed."""
    return build_graph(checkpointer=MemorySaver())


@pytest.fixture
def mock_handlers():
    """Patch chatbot handlers so no agent or WhatsApp client is invoked during webhook tests."""
    with patch("app.core.chatbot.handlers.handle_message_event", new_callable=AsyncMock) as mock_msg, \
         patch("app.core.chatbot.handlers.handle_status_event", new_callable=AsyncMock) as mock_status:
        yield {"message": mock_msg, "status": mock_status}
