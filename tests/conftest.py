from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from app.agent.graph import build_graph
from app.api.main import app
from app.core.config import settings


@pytest.fixture(autouse=True)
def patch_settings():
    """Force test credential defaults regardless of .env content."""
    with patch.object(settings, "whatsapp_verify_token", "dev-verify-token"), \
         patch.object(settings, "whatsapp_app_secret", "dev-secret"):
        yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


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
def mock_background_task():
    """Patch process_whatsapp_message so no agent is invoked during webhook tests."""
    with patch("app.agent.tasks.process_whatsapp_message", new_callable=AsyncMock) as mock_task:
        yield mock_task
