import logging
import os

from langchain_aws import ChatBedrock
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.prompts import load_active_prompt
from app.agent.state import AgentState
from app.agent.tools import ALL_TOOLS
from app.core.config import settings

logger = logging.getLogger(__name__)

_graph_instance = None


def _build_checkpointer():
    """Return a PyMySQLSaver if DB is configured and checkpoint tables exist, else MemorySaver.

    We never call setup() — checkpoint tables are created by the Rails monolith migrations.
    If the tables are missing we fall back to MemorySaver and log a warning.
    """
    if not all([settings.db_host, settings.db_user, settings.db_pass, settings.db_name]):
        logger.info("DB not configured — using MemorySaver (in-process, non-persistent)")
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
    try:
        import pymysql
        from langgraph.checkpoint.mysql.pymysql import ShallowPyMySQLSaver as ShallowMySQLSaver
        ssl = {"ca": settings.db_ssl_cert} if os.path.exists(settings.db_ssl_cert) else None
        conn = pymysql.connect(
            host=settings.db_host,
            user=settings.db_user,
            password=settings.db_pass,
            database=settings.db_name,
            ssl=ssl,
            autocommit=True,
        )
        # Verify tables exist before returning the saver — we are a consumer, not an admin.
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM checkpoints LIMIT 1")
        saver = ShallowMySQLSaver(conn)
        logger.info("MySQL checkpointer ready (host=%s db=%s)", settings.db_host, settings.db_name)
        return saver
    except Exception as exc:
        logger.warning("MySQL checkpointer unavailable, falling back to MemorySaver: %s", exc)
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()


def get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph(checkpointer=_build_checkpointer())
    return _graph_instance


def build_graph(checkpointer=None):
    """Build and compile the LangGraph ReAct agent.

    Pass a checkpointer explicitly in tests (e.g. MemorySaver()).
    Production uses get_graph() which selects the checkpointer automatically.
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

    # TODO: context strategy — incremental summarization
    # Current: sliding window (last _CTX_WINDOW msgs). Full history in checkpointer.
    # Future: if unsummarized msgs > _CTX_WINDOW, summarize oldest batch → save to
    #   conversation_summaries (conversation_id, summary_text, covered_through_message_id).
    #   LLM context = system + latest_summary + last _CTX_WINDOW msgs.
    #   Scope to 24h (aligns with WhatsApp customer window). Only summarize new msgs
    #   since last summary (covered_through_message_id as cursor).
    _CTX_WINDOW = 20

    def _agent_node(state: AgentState) -> dict:
        system_msg = SystemMessage(content=load_active_prompt())
        messages = list(state["messages"])[-_CTX_WINDOW:]
        response = llm_with_tools.invoke([system_msg] + messages)
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
