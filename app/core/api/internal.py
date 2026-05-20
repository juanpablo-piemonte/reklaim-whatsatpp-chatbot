import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.core.config import settings
from app.core.db.engine import get_db
from app.core.db.repositories import conversation_repo, message_repo
from app.core.security import require_api_key
from app.whatsapp.client import whatsapp_client
from app.whatsapp.models import OutboundText

logger = logging.getLogger(__name__)

router = APIRouter()


class SenderInfo(BaseModel):
    type: Literal["reviewer", "campaign"]
    reviewer_id: Optional[int] = None
    campaign_id: Optional[int] = None

    @model_validator(mode="after")
    def _check_id_for_type(self):
        if self.type == "reviewer" and self.reviewer_id is None:
            raise ValueError("sender.reviewer_id required when sender.type == 'reviewer'")
        if self.type == "campaign" and self.campaign_id is None:
            raise ValueError("sender.campaign_id required when sender.type == 'campaign'")
        return self


class RefInfo(BaseModel):
    type: str
    id: int


class OutboundRequest(BaseModel):
    body: str = Field(min_length=1)
    sender: SenderInfo
    conversation_id: Optional[int] = None
    dealer_phone: Optional[str] = None
    template_id: Optional[int] = None
    ref: Optional[RefInfo] = None
    idempotency_key: Optional[str] = None

    @model_validator(mode="after")
    def _require_one_target(self):
        if (self.conversation_id is None) == (self.dealer_phone is None):
            raise ValueError("exactly one of conversation_id or dealer_phone is required")
        return self


class OutboundResponse(BaseModel):
    message_id: int
    wamid: str
    conversation_id: int
    status: Literal["sent"]


@router.post("/outbound", response_model=OutboundResponse, dependencies=[Depends(require_api_key)])
async def post_outbound(payload: OutboundRequest):
    db = next(get_db())

    if payload.conversation_id is not None:
        conv = conversation_repo.get_by_id(db, payload.conversation_id)
        if conv is None:
            raise HTTPException(status_code=422, detail=f"conversation {payload.conversation_id} not found")
    else:
        conv = conversation_repo.get_or_create(
            db,
            phone_number_id=settings.whatsapp_phone_number_id,
            from_phone=payload.dealer_phone,
        )

    if payload.idempotency_key:
        existing = message_repo.find_by_idempotency_key(db, conv.id, payload.idempotency_key)
        if existing is not None:
            return OutboundResponse(
                message_id=existing.id,
                wamid=existing.wamid,
                conversation_id=conv.id,
                status="sent",
            )

    if payload.template_id is not None:
        logger.warning(
            "[internal/outbound] template_id=%s present but Meta template send is deferred; sending as free text",
            payload.template_id,
        )

    dealer_phone = payload.dealer_phone or conv.from_phone

    try:
        send_result = whatsapp_client.send(OutboundText(to=dealer_phone, body=payload.body))
    except Exception as exc:
        logger.exception("[internal/outbound] meta send failed conversation_id=%s: %s", conv.id, exc)
        raise HTTPException(status_code=502, detail=f"meta send failed: {exc}")

    raw_payload = {
        "sender_type": payload.sender.type,
        "reviewer_id": payload.sender.reviewer_id,
        "campaign_id": payload.sender.campaign_id,
        "idempotency_key": payload.idempotency_key,
        "ref": payload.ref.model_dump() if payload.ref else None,
    }

    msg = message_repo.create(
        db,
        conversation_id=conv.id,
        wamid=send_result.wamid,
        message_type="text",
        direction="outbound",
        body=payload.body,
        raw_payload=raw_payload,
    )
    if msg is None:
        logger.warning("[internal/outbound] duplicate wamid=%s on insert; rare", send_result.wamid)
        from app.core.db.models import Message
        msg = db.query(Message).filter_by(wamid=send_result.wamid).first()

    return OutboundResponse(
        message_id=msg.id,
        wamid=msg.wamid,
        conversation_id=conv.id,
        status="sent",
    )
