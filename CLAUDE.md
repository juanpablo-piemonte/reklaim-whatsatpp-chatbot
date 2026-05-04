# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make install   # Create .venv and install all deps (including [dev] extras) — requires Python 3.12
make run       # Start Uvicorn on :8000, output to logs/uvicorn.log
make stop      # Kill running server
make logs      # Tail uvicorn.log
make test      # Run pytest -v (no external services needed)
make clean     # Remove __pycache__, .pids, logs/
```

Run a single test file:
```bash
.venv/bin/pytest tests/test_webhooks.py -v
```

## Architecture

This is a WhatsApp AI chatbot for Reklaim car dealers. Meta sends webhook POSTs → FastAPI handler → BackgroundTask → LangGraph agent → WhatsApp reply.

**Request flow:**
1. `POST /webhooks/whatsapp` — HMAC-SHA256 verified (via `WHATSAPP_APP_SECRET`), extracts dealer phone + message text, enqueues `process_whatsapp_message` as a FastAPI `BackgroundTask` so the webhook returns in < 200ms
2. `app/agent/tasks.py` — invokes the compiled LangGraph agent with `dealer_phone` as `thread_id` (maintains per-dealer conversation history)
3. `app/agent/graph.py` — ReAct agent (agent → tools → agent → END) using `ChatBedrock` (default: `us.amazon.nova-pro-v1:0`)
4. `app/services/whatsapp_client.py` — sends the response back via Meta Cloud API

**Key modules:**
- `app/api/` — FastAPI route definitions; `chat.py` has `/chat/test` for testing the agent directly
- `app/agent/graph.py` — LangGraph `StateGraph`; `get_graph()` returns a compiled agent (cached module-level)
- `app/agent/state.py` — `AgentState` TypedDict: `messages`, `dealer_phone`, `stage`, `metadata`
- `app/agent/tools/` — LangChain tools; add new tools here and register them in `__init__.py` (`ALL_TOOLS`)
- `app/agent/prompts.py` — `load_active_prompt()` returns system prompt (hardcoded; TODO: fetch from Rails)
- `app/services/monolith_client.py` — HTTP client to Reklaim Rails API (currently returns stub data)
- `app/db/` — SQLAlchemy models (`Conversation`, `Message`) and MySQL engine; **defined but not yet wired into the agent** — conversation state is currently in-memory via `MemorySaver`
- `app/core/config.py` — Pydantic `Settings` loaded from `.env`

## Environment Setup

Copy `.env.example` to `.env`. Required variables:

| Variable | Purpose |
|---|---|
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Bedrock LLM access |
| `BEDROCK_MODEL_ID` | Model ARN (default: `us.amazon.nova-pro-v1:0`) |
| `WHATSAPP_APP_SECRET` | HMAC verification of incoming webhooks |
| `WHATSAPP_VERIFY_TOKEN` | Meta webhook subscription handshake |
| `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | Sending messages via Meta API |
| `REKLAIM_API_URL`, `DEALERS_CHATBOT_API_KEY` | Reklaim Rails monolith |
| `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME` | MySQL (RDS) for conversation persistence |

For local dev without real credentials, `config.py` ships with `dev-*` defaults for all WhatsApp/Reklaim vars; only AWS credentials are required for live LLM calls.

## Testing

Tests use `unittest.mock.patch` to mock Bedrock (no real AWS calls). WhatsApp send is never invoked. `MemorySaver` is used as checkpointer so no DB is needed. All tests are runnable with just `make test`.

## Active TODOs in Code

- `prompts.py` — `load_active_prompt()` should fetch named prompts from the Rails monolith instead of being hardcoded
- `app/db/` models are ready but not integrated — the agent still uses `MemorySaver`; MySQL checkpointer integration is pending
- `MonolithClient` returns stub data; real HTTP calls to Rails are not yet implemented
