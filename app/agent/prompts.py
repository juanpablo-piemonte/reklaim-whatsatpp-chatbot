SYSTEM_PROMPT = (
    "You are a helpful assistant for Reklaim, a luxury goods platform. "
    "You help dealers submit offers for purchase orders."
)


def load_active_prompt(name: str = "default") -> str:
    # TODO: fetch named prompt from monolith via monolith_client
    return SYSTEM_PROMPT
