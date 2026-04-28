# reklaim-whatsapp-ai

A standalone Python microservice that powers a WhatsApp chatbot for Reklaim, a luxury goods platform. Dealers send messages via WhatsApp; the service receives them through a Meta webhook, processes each message asynchronously with a LangGraph agent backed by AWS Bedrock (Claude 3.5 Sonnet), and sends replies back through the WhatsApp Cloud API. It integrates with a Rails monolith for business context (purchase orders, prompts) over an internal HTTP API.

## Local setup

```bash
cp .env.example .env          # fill in your credentials (see comments in the file)
docker-compose up -d          # start Redis
pip install -e ".[dev]"
uvicorn app.api.main:app --reload                         # start FastAPI on port 8000
celery -A app.worker.celery_app worker --loglevel=info    # start worker (separate terminal)
```

Python 3.12 and Docker are required. Create a virtualenv first if you haven't:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
```

## Running tests

```bash
pytest
```

No external services are required — Bedrock is mocked via `unittest.mock`, Redis is replaced with `MemorySaver`, and WhatsApp calls never leave the process.

## Testing Bedrock locally (without WhatsApp)

Once `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION` are set in `.env`, use the `/chat/test` endpoint to talk directly to the agent:

```bash
curl -s -X POST http://localhost:8000/chat/test \
  -H "Content-Type: application/json" \
  -d '{"phone": "+15550001234", "message": "Hello, what can you help me with?"}' | jq
```

Conversation history is preserved per `phone` value (stored in Redis via RedisSaver).

## Running with ngrok (WhatsApp webhook)

1. Install ngrok: https://ngrok.com/download
2. Start the FastAPI server: `uvicorn app.api.main:app --reload --port 8000`
3. In another terminal: `ngrok http 8000`
4. Copy the https forwarding URL (e.g. `https://abc123.ngrok.io`)
5. In Meta for Developers → your App → WhatsApp → Configuration:
   - Webhook URL: `https://abc123.ngrok.io/webhooks/whatsapp`
   - Verify token: value of `WHATSAPP_VERIFY_TOKEN` in your `.env`
   - Subscribe to: **messages**
6. Send a WhatsApp message to your test number — watch the terminal

> **AWS IAM requirement:** the IAM user in your `.env` needs `bedrock:InvokeModel` permission on
> `arn:aws:bedrock:{region}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0`

## Architecture

This service sits between Meta's WhatsApp Cloud API and Reklaim's Rails monolith. Incoming messages arrive at `POST /webhooks/whatsapp`, are HMAC-verified, and immediately dispatched to a Celery task queue (backed by Redis) so the webhook returns within Meta's 20-second timeout. The Celery worker picks up each task, runs it through a LangGraph `StateGraph` that maintains per-dealer conversation history (keyed by phone number) using a Redis checkpointer, and sends the agent's reply back via the WhatsApp Cloud API. The Rails monolith is called to fetch open purchase orders and the active system prompt, keeping business logic out of this service.

## What's real vs stubbed

| Component | Local dev | Notes |
|---|---|---|
| AWS Bedrock (Claude 3.5 Sonnet) | **Real** | Requires AWS credentials in `.env` |
| WhatsApp Cloud API | **Real** | Requires Meta credentials in `.env` |
| Redis (broker + checkpointer) | **Real** | `docker-compose up -d` |
| HMAC verification | **Real** | Uses `WHATSAPP_APP_SECRET` from `.env` |
| Rails monolith | **Stub** | `MonolithClient` returns hardcoded mock data |
| Bedrock (in tests) | **Mocked** | `unittest.mock.patch` — no AWS calls in `pytest` |
| WhatsApp (in tests) | **Mocked** | Celery task `.delay()` is patched |

## Project layout

```
app/
  api/          FastAPI app factory, webhook endpoints, /chat/test
  worker/       Celery app, process_whatsapp_message task
  agent/        LangGraph graph, AgentState, prompts
  services/     WhatsApp (Meta API) and monolith clients
  core/         Settings (pydantic-settings), HMAC security helper
tests/
docker-compose.yml
.env.example
```
