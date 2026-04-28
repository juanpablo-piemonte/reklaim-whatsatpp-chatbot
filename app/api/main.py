import logging

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.webhooks import router as webhooks_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Reklaim WhatsApp AI", version="0.1.0")

app.include_router(webhooks_router, prefix="/webhooks")
app.include_router(chat_router, prefix="/chat")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
