# reklaim-whatsapp-ai

A Python microservice that powers a WhatsApp chatbot for Reklaim, a luxury goods marketplace. Dealers send messages via WhatsApp; the service receives them through a Meta webhook, processes each message with a LangGraph ReAct agent backed by AWS Bedrock (Amazon Nova Pro), and sends replies back through the WhatsApp Cloud API. Integrates with the Reklaim Rails monolith over an internal HTTP API.

## Local setup

Python 3.12 required.

```bash
cp .env.example .env   # fill in credentials
make install           # creates .venv and installs all deps
make cert              # downloads RDS SSL cert (global-bundle.pem)
make run               # starts Uvicorn on :8000
```

## Make commands

| Command | Description |
|---|---|
| `make run` | Start Uvicorn on :8000 (logs to `logs/uvicorn.log`) |
| `make stop` | Stop the running server |
| `make restart` | Stop and start (alias for `make run`) |
| `make logs` | Tail live server output |
| `make test` | Run the full pytest suite |
| `make install` | Create `.venv` and install all dependencies |
| `make cert` | Download the RDS SSL CA bundle (`global-bundle.pem`) |
| `make cleanup` | Delete checkpoint rows for inactive conversations (48h+) |
| `make cleanup-dry` | Preview what `make cleanup` would delete without touching anything |
| `make clean` | Stop server and remove `__pycache__`, `.pids`, `logs/` |

## Tests

```bash
make test
# or a single file:
.venv/bin/pytest tests/test_handlers.py -v
```

No external services required — Bedrock is mocked, MemorySaver handles state in-process, and WhatsApp calls never leave the process.

## Testing the agent locally (without WhatsApp)

With AWS credentials set in `.env`, hit `/chat/test` to talk directly to the agent:

```bash
curl -s -X POST http://localhost:8000/chat/test \
  -H "Content-Type: application/json" \
  -d '{"phone": "+15550001234", "message": "Hello, what can you help me with?"}' | jq
```

## Webhook setup (ngrok)

1. `make run`
2. In another terminal: `ngrok http 8000`
3. In Meta for Developers → your App → WhatsApp → Configuration:
   - Webhook URL: `https://<ngrok-id>.ngrok.io/webhooks/whatsapp`
   - Verify token: value of `WHATSAPP_VERIFY_TOKEN` in `.env`
   - Subscribe to: **messages**
4. Send a WhatsApp message to your test number and watch `make logs`

## Architecture

```
Meta webhook → POST /webhooks/whatsapp (HMAC-SHA256 verified)
    → FastAPI BackgroundTask (returns 200 immediately)
        → mark message as read
        → persist inbound message to DB
        → LangGraph ReAct agent (ShallowPyMySQLSaver checkpointer)
            → ChatBedrock (Amazon Nova Pro)
            → tools: Reklaim monolith API
        → persist agent run (tokens, latency) to DB
        → send reply via WhatsApp Cloud API
        → persist outbound message to DB
```

**Key modules:**

| Path | Responsibility |
|---|---|
| `app/whatsapp/` | Meta webhook models, payload parser, WhatsApp HTTP client |
| `app/agent/` | LangGraph graph, AgentState, system prompt, tools |
| `app/core/api/` | FastAPI routes (`/webhooks`, `/chat`, `/health`) |
| `app/core/chatbot/` | Orchestration: handlers, mapper, session |
| `app/core/db/` | SQLAlchemy models, engine, repositories |

**Conversation memory:** `ShallowPyMySQLSaver` — one checkpoint row per dealer (phone number), updated in place on every turn. Survives deploys and multi-worker ECS. Context window: last 20 messages sent to the LLM.

## Component status

| Component | Status | Notes |
|---|---|---|
| AWS Bedrock (Nova Pro) | Real | Requires AWS credentials |
| WhatsApp Cloud API | Real | Requires Meta credentials |
| HMAC verification | Real | Uses `WHATSAPP_APP_SECRET` |
| Conversation memory | MySQL | `ShallowPyMySQLSaver`, survives restarts |
| DB persistence | Real | Conversations, messages, agent runs in RDS |
| Rails monolith | Real (dev) | Stub data in local dev without `REKLAIM_API_URL` |
| Bedrock (in tests) | Mocked | No AWS calls during `pytest` |
| WhatsApp (in tests) | Mocked | Handlers patched at webhook level |

## Deployment

Pushes to `dev` trigger `.github/workflows/deploy-dev.yaml` → builds Docker image → pushes to ECR → force-deploys ECS service.

Required GitHub secrets (same IAM credentials as the reklaim repo):
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

App credentials are injected at runtime from AWS Secrets Manager (`dev/reklaim-whatsapp-chatbot`). DB schema is managed by the Rails monolith repository.

## Project layout

```
app/
  whatsapp/        Meta webhook models, parser, WhatsApp HTTP client
  agent/           LangGraph graph, AgentState, prompts, tools
  core/
    api/           FastAPI app, webhook + chat routes, /health
    chatbot/       Handlers, mapper (inbound→agent→outbound), session
    db/            SQLAlchemy models, engine, repositories
    config.py      Pydantic settings (loaded from .env)
    security.py    HMAC-SHA256 signature verification
scripts/
  cleanup_checkpoints.py   Manual cleanup of inactive checkpoint rows
tests/
.env.example
Dockerfile
Makefile
```
