from langchain_core.tools import tool


@tool
def no_op_tool(query: str) -> str:
    """Placeholder tool. Replace with real tool implementations."""
    return f"[no-op] received: {query}"
