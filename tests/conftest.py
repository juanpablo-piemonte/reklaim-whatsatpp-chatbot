from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from app.agent.graph import build_graph
from app.api.main import app


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
    mock_llm.invoke.return_value = fake
    with patch("app.agent.graph.ChatBedrock", return_value=mock_llm):
        yield mock_llm


@pytest.fixture
def graph(mock_bedrock):
    """Compiled agent graph with MemorySaver and mocked Bedrock — no external services needed."""
    return build_graph(checkpointer=MemorySaver())


@pytest.fixture
def mock_celery_task():
    """Patch Celery task .delay() so no worker is needed during tests."""
    with patch("app.worker.tasks.process_whatsapp_message.delay") as mock_delay:
        mock_delay.return_value = None
        yield mock_delay
