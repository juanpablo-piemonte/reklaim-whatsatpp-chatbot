import logging

from fastapi import FastAPI

from app.core.api.chat import router as chat_router
from app.core.api.webhooks import router as webhooks_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Reklaim WhatsApp AI", version="0.1.0")

app.include_router(webhooks_router, prefix="/webhooks")
app.include_router(chat_router, prefix="/chat")


@app.get("/health")
async def health() -> dict:
    from app.core.config import settings
    db_configured = all([settings.db_host, settings.db_user, settings.db_pass, settings.db_name])
    if db_configured:
        from app.core.db.engine import check_db_connection
        db_ok = check_db_connection()
        return {"status": "ok", "db": "connected" if db_ok else "unreachable"}
    return {"status": "ok", "db": "not_configured"}
