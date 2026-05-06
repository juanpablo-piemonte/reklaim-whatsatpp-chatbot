from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.agent.graph import build_graph


def test_graph_builds():
    assert build_graph(checkpointer=MemorySaver()) is not None


def test_agent_responds(graph):
    """Agent returns a non-empty AIMessage for a simple user message."""
    result = graph.invoke(
        {
            "messages": [HumanMessage(content="Hello")],
            "from_phone": "15559876543",
            "stage": "greeting",
            "metadata": {},
        },
        config={"configurable": {"thread_id": "test-responds"}},
    )
    last = result["messages"][-1]
    assert isinstance(last, AIMessage)
    assert last.content


def test_agent_state_persists(graph):
    """Second invocation on the same thread_id retains messages from the first."""
    config = {"configurable": {"thread_id": "test-persists"}}
    base = {"from_phone": "15550001111", "stage": "greeting", "metadata": {}}

    graph.invoke({"messages": [HumanMessage(content="First message")], **base}, config=config)
    result = graph.invoke({"messages": [HumanMessage(content="Second message")], **base}, config=config)

    all_content = [m.content for m in result["messages"]]
    assert any("First message" in c for c in all_content)
    assert any("Second message" in c for c in all_content)


def test_agent_calls_llm_with_messages(graph, mock_bedrock):
    """LLM is invoked with the conversation history."""
    graph.invoke(
        {
            "messages": [HumanMessage(content="What can you help me with?")],
            "from_phone": "15550002222",
            "stage": "greeting",
            "metadata": {},
        },
        config={"configurable": {"thread_id": "test-llm-call"}},
    )
    bound = mock_bedrock.bind_tools.return_value
    bound.invoke.assert_called_once()
    call_args = bound.invoke.call_args[0][0]
    assert call_args[-1].content == "What can you help me with?"


def test_agent_preserves_state_fields(graph):
    result = graph.invoke(
        {
            "messages": [HumanMessage(content="hi")],
            "from_phone": "15557654321",
            "stage": "greeting",
            "metadata": {"dealer_id": 42},
        },
        config={"configurable": {"thread_id": "test-fields"}},
    )
    assert result["from_phone"] == "15557654321"
    assert result["metadata"] == {"dealer_id": 42}
