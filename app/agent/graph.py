import logging

from langchain_aws import ChatBedrock
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.prompts import load_active_prompt
from app.agent.state import AgentState
from app.agent.tools import ALL_TOOLS
from app.core.config import settings

logger = logging.getLogger(__name__)

# Process-level singleton — shared between the webhook path and /chat/test.
# MemorySaver is in-process; this ensures both paths use the same instance
# and conversation history is preserved across calls within a process lifetime.
_graph_instance = None


def get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance


def build_graph(checkpointer=None):
    """Build and compile the LangGraph ReAct agent.

    Pass a checkpointer explicitly in tests (e.g. MemorySaver()).
    Production uses a module-level MemorySaver via get_graph().
    """
    if checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()

    llm = ChatBedrock(
        model_id=settings.bedrock_model_id,
        region_name=settings.aws_region,
        model_kwargs={"max_tokens": 1024},
    )
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def _agent_node(state: AgentState) -> dict:
        system_msg = SystemMessage(content=load_active_prompt())
        response = llm_with_tools.invoke([system_msg] + list(state["messages"]))
        logger.debug("Agent response: tool_calls=%r", getattr(response, "tool_calls", []))
        return {"messages": [response]}

    tool_node = ToolNode(ALL_TOOLS)

    builder = StateGraph(AgentState)
    builder.add_node("agent", _agent_node)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)  # → "tools" or END
    builder.add_edge("tools", "agent")  # loop back after tool execution

    return builder.compile(checkpointer=checkpointer)
