"""Service-to-service endpoints called by the Rails monolith.

- POST /internal/outbound — campaign + reviewer sends (X-Internal-Token).
- POST /internal/conversations/{id}/messages — Epic 4 reviewer dashboard
  replies via ChatbotClient (X-API-Key).
"""

import logging
import secrets
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db.engine import get_db
from app.core.db.repositories import conversation_repo, message_repo
from app.core.security import require_api_key
from app.whatsapp.client import whatsapp_client
from app.whatsapp.models import OutboundText

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_internal_token(request: Request) -> None:
    presented = request.headers.get("X-Internal-Token", "")
    expected = settings.chatbot_internal_token or ""
    if not presented or not expected or not secrets.compare_digest(
        presented.encode(), expected.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing X-Internal-Token",
        )


# ---------------------------------------------------------------------------
# POST /internal/outbound — campaigns + unified reviewer sends
# ---------------------------------------------------------------------------

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


@router.post("/outbound", response_model=OutboundResponse)
async def post_outbound(
    payload: OutboundRequest,
    _: None = Depends(_require_internal_token),
):
    db = next(get_db())

    if payload.conversation_id is not None:
        conv = conversation_repo.get_by_id(db, payload.conversation_id)
        if conv is None:
            raise HTTPException(
                status_code=422,
                detail=f"conversation {payload.conversation_id} not found",
            )
    else:
        conv = conversation_repo.get_or_create(
            db,
            phone_number_id=settings.whatsapp_phone_number_id,
            from_phone=payload.dealer_phone,
        )

    if payload.idempotency_key:
        existing = message_repo.find_by_idempotency_key(
            db, conv.id, payload.idempotency_key
        )
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
        logger.exception(
            "[internal/outbound] meta send failed conversation_id=%s: %s", conv.id, exc
        )
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
        logger.warning(
            "[internal/outbound] duplicate wamid=%s on insert; rare", send_result.wamid
        )
        from app.core.db.models import Message

        msg = db.query(Message).filter_by(wamid=send_result.wamid).first()

    return OutboundResponse(
        message_id=msg.id,
        wamid=msg.wamid,
        conversation_id=conv.id,
        status="sent",
    )


# ---------------------------------------------------------------------------
# POST /internal/conversations/{id}/messages — Epic 4 dashboard reviewer reply
# ---------------------------------------------------------------------------

class ReviewerReplyRequest(BaseModel):
    body: str = Field(..., min_length=1, description="Reviewer-typed reply body.")
    reviewer_account_id: int | None = Field(
        default=None,
        description="Rails account id of the reviewer, stashed in raw_payload for audit.",
    )


class ReviewerReplyResponse(BaseModel):
    provider_message_id: str | None
    status: str


@router.post(
    "/conversations/{conversation_id}/messages",
    dependencies=[Depends(require_api_key)],
    response_model=ReviewerReplyResponse,
)
def create_reviewer_message(
    payload: ReviewerReplyRequest,
    conversation_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ReviewerReplyResponse:
    """Send a reviewer-typed reply via Meta WhatsApp and persist the outbound row.

    Called by Rails `ChatbotClient` when a reviewer hits Send in the dashboard.
    """
    conv = conversation_repo.get_by_id(db, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")

    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="body cannot be blank")

    try:
        send_result = whatsapp_client.send(OutboundText(to=conv.from_phone, body=body))
    except Exception as exc:
        logger.error(
            "[internal] WhatsApp send failed conversation=%s reviewer=%s: %s",
            conversation_id,
            payload.reviewer_account_id,
            exc,
        )
        raise HTTPException(status_code=502, detail="whatsapp send failed") from exc

    provider_wamid = send_result.wamid
    if not provider_wamid:
        logger.error(
            "[internal] WhatsApp send returned no wamid conversation=%s body=%r",
            conversation_id,
            body[:80],
        )
        raise HTTPException(status_code=502, detail="whatsapp send returned no message id")

    raw_payload = {
        "sender_type": "reviewer",
        "source": "rails_internal_api",
    }
    if payload.reviewer_account_id is not None:
        raw_payload["reviewer_account_id"] = payload.reviewer_account_id

    persisted = message_repo.create(
        db,
        conversation_id=conv.id,
        wamid=provider_wamid,
        message_type="text",
        direction="outbound",
        body=body,
        raw_payload=raw_payload,
    )
    if persisted is None:
        logger.info(
            "[internal] duplicate wamid on reviewer reply conversation=%s wamid=%s",
            conversation_id,
            provider_wamid,
        )

    return ReviewerReplyResponse(provider_message_id=provider_wamid, status="sent")
