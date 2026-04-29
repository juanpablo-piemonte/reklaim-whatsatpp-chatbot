# reklaim-whatsapp-ai

A standalone Python microservice that powers a WhatsApp chatbot for Reklaim, a luxury goods platform. Dealers send messages via WhatsApp; the service receives them through a Meta webhook, processes each message asynchronously with FastAPI BackgroundTasks and a LangGraph agent backed by AWS Bedrock (Claude 3.5 Sonnet), and sends replies back through the WhatsApp Cloud API. It integrates with a Rails monolith for business context (purchase orders, prompts) over an internal HTTP API.

## Local setup

```bash
cp .env.example .env   # fill in AWS + WhatsApp credentials
make install
make run
```

Python 3.12 is required.

## Running tests

```bash
pytest
```

No external services are required — Bedrock is mocked via `unittest.mock`, MemorySaver handles conversation state in-process, and WhatsApp calls never leave the process.

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

This service sits between Meta's WhatsApp Cloud API and Reklaim's Rails monolith. Incoming messages arrive at `POST /webhooks/whatsapp`, are HMAC-verified, and immediately dispatched to a FastAPI BackgroundTask so the webhook returns within Meta's 20-second timeout. The background task runs each message through a LangGraph `StateGraph` that maintains per-dealer conversation history (keyed by phone number) using an in-memory checkpointer, and sends the agent's reply back via the WhatsApp Cloud API. The Rails monolith is called to fetch open purchase orders and the active system prompt, keeping business logic out of this service.

## What's real vs stubbed

| Component | Local dev | Notes |
|---|---|---|
| AWS Bedrock (Claude 3.5 Sonnet) | **Real** | Requires AWS credentials in `.env` |
| WhatsApp Cloud API | **Real** | Requires Meta credentials in `.env` |
| Conversation memory | **In-process** | `MemorySaver` — resets on restart, MySQL checkpointer TBD |
| HMAC verification | **Real** | Uses `WHATSAPP_APP_SECRET` from `.env` |
| Rails monolith | **Stub** | `MonolithClient` returns hardcoded mock data |
| Bedrock (in tests) | **Mocked** | `unittest.mock.patch` — no AWS calls in `pytest` |
| WhatsApp (in tests) | **Mocked** | Background task is patched |

## Project layout

```
app/
  api/          FastAPI app factory, webhook endpoints, /chat/test
  agent/        LangGraph graph, AgentState, prompts, process_whatsapp_message task
  services/     WhatsApp (Meta API) and monolith clients
  core/         Settings (pydantic-settings), HMAC security helper
tests/
.env.example
```
