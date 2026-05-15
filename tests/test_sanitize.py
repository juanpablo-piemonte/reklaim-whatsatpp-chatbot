from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.graph import _sanitize_message_window


def _tool_msg(tool_call_id: str) -> ToolMessage:
    return ToolMessage(content="ok", tool_call_id=tool_call_id)


def _ai_with_tool(call_id: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"id": call_id, "name": "t", "args": {}}])


# --- happy path ---

def test_clean_window_unchanged():
    msgs = [HumanMessage(content="hi"), AIMessage(content="hello")]
    assert _sanitize_message_window(msgs) == msgs


def test_complete_tool_call_preserved():
    ai = _ai_with_tool("id1")
    tr = _tool_msg("id1")
    hu = HumanMessage(content="next")
    result = _sanitize_message_window([hu, ai, tr])
    assert result == [hu, ai, tr]


# --- error 1: window starts with non-HumanMessage ---

def test_leading_ai_message_trimmed():
    ai = AIMessage(content="hello")
    hu = HumanMessage(content="world")
    result = _sanitize_message_window([ai, hu])
    assert result == [hu]


def test_leading_tool_messages_trimmed():
    tr = _tool_msg("x")
    hu = HumanMessage(content="hi")
    result = _sanitize_message_window([tr, hu])
    assert result == [hu]


def test_all_non_human_returns_empty():
    result = _sanitize_message_window([AIMessage(content="a"), AIMessage(content="b")])
    assert result == []


# --- error 2: dangling tool call ---

def test_dangling_tool_call_dropped():
    hu = HumanMessage(content="first")
    dangling_ai = _ai_with_tool("orphan")
    hu2 = HumanMessage(content="second")
    result = _sanitize_message_window([hu, dangling_ai, hu2])
    assert result == [hu, hu2]


def test_dangling_tool_call_with_partial_results_dropped():
    hu = HumanMessage(content="first")
    ai = _ai_with_tool("id1")
    ai.tool_calls = [
        {"id": "id1", "name": "t", "args": {}},
        {"id": "id2", "name": "t", "args": {}},
    ]
    tr_partial = _tool_msg("id1")  # id2 never arrived
    hu2 = HumanMessage(content="second")
    result = _sanitize_message_window([hu, ai, tr_partial, hu2])
    assert result == [hu, hu2]


def test_dangling_at_start_then_trimmed():
    dangling_ai = _ai_with_tool("orphan")
    hu = HumanMessage(content="hi")
    result = _sanitize_message_window([dangling_ai, hu])
    assert result == [hu]


def test_complete_tool_call_followed_by_dangling():
    hu1 = HumanMessage(content="first")
    good_ai = _ai_with_tool("good")
    good_tr = _tool_msg("good")
    bad_ai = _ai_with_tool("bad")
    hu2 = HumanMessage(content="second")
    result = _sanitize_message_window([hu1, good_ai, good_tr, bad_ai, hu2])
    assert result == [hu1, good_ai, good_tr, hu2]
