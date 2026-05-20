import time
from unittest.mock import MagicMock, patch

import pytest

from app.agent import prompts


@pytest.fixture(autouse=True)
def clear_cache():
    prompts._CACHE.clear()
    yield
    prompts._CACHE.clear()


def _mock_response(body: str, status_code: int = 200):
    resp = MagicMock()
    resp.json.return_value = {"name": "default", "body": body, "version": 1}
    resp.raise_for_status = MagicMock() if status_code == 200 else MagicMock(side_effect=Exception(f"HTTP {status_code}"))
    return resp


def test_fresh_fetch_populates_cache():
    with patch("app.agent.prompts.httpx.get", return_value=_mock_response("from rails")) as mock_get:
        body = prompts.load_active_prompt("default")
        assert body == "from rails"
        assert "default" in prompts._CACHE
        mock_get.assert_called_once()


def test_subsequent_call_within_ttl_serves_cache():
    with patch("app.agent.prompts.httpx.get", return_value=_mock_response("v1")) as mock_get:
        prompts.load_active_prompt("default")
        prompts.load_active_prompt("default")
        assert mock_get.call_count == 1


def test_stale_cache_after_ttl_refetches():
    with patch("app.agent.prompts.httpx.get", return_value=_mock_response("v1")) as mock_get:
        prompts.load_active_prompt("default")
        prompts._CACHE["default"] = (time.monotonic() - prompts._CACHE_TTL_S - 1, "v1")
        prompts.load_active_prompt("default")
        assert mock_get.call_count == 2


def test_serves_stale_cache_on_http_error():
    with patch("app.agent.prompts.httpx.get", return_value=_mock_response("v1")):
        prompts.load_active_prompt("default")
    prompts._CACHE["default"] = (time.monotonic() - prompts._CACHE_TTL_S - 1, "v1")
    with patch("app.agent.prompts.httpx.get", side_effect=Exception("network down")):
        body = prompts.load_active_prompt("default")
        assert body == "v1"


def test_fallback_when_no_cache_and_http_fails():
    with patch("app.agent.prompts.httpx.get", side_effect=Exception("network down")):
        body = prompts.load_active_prompt("default")
        assert body == prompts._FALLBACK_PROMPT


def test_per_name_caching():
    with patch("app.agent.prompts.httpx.get") as mock_get:
        mock_get.side_effect = [_mock_response("A"), _mock_response("B")]
        a = prompts.load_active_prompt("greeting")
        b = prompts.load_active_prompt("negotiation")
        assert a == "A"
        assert b == "B"
        assert "greeting" in prompts._CACHE
        assert "negotiation" in prompts._CACHE
