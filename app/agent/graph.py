import logging

from langchain_aws import ChatBedrock
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph

from app.agent.prompts import load_active_prompt
from app.agent.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)


def _agent_node(state: AgentState) -> dict:
    llm = ChatBedrock(
        model_id=settings.bedrock_model_id,
        region_name=settings.aws_region,
        model_kwargs={"max_tokens": 1024},
    )
    system_msg = SystemMessage(content=load_active_prompt())
    response = llm.invoke([system_msg] + list(state["messages"]))
    logger.debug("Bedrock response: %r", response.content[:120])
    return {"messages": [response]}


def build_graph(checkpointer=None):
    """Build and compile the LangGraph agent.

    Pass a checkpointer explicitly in tests (e.g. MemorySaver()).
    In production MemorySaver is used until a persistent DB checkpointer is configured.
    """
    if checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()

    builder = StateGraph(AgentState)
    builder.add_node("agent", _agent_node)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)

    return builder.compile(checkpointer=checkpointer)
