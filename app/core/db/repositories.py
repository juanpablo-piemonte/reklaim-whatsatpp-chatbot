import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db.models import AgentRun, Conversation, Message

_CUSTOMER_WINDOW_HOURS = 24

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _window_expires_at() -> datetime:
    return _now() + timedelta(hours=_CUSTOMER_WINDOW_HOURS)


class ConversationRepository:
    def get_or_create(
        self,
        db: Session,
        phone_number_id: str,
        from_phone: str,
        contact_name: str | None = None,
    ) -> Conversation:
        conv = (
            db.query(Conversation)
            .filter_by(phone_number_id=phone_number_id, from_phone=from_phone)
            .first()
        )
        if conv:
            conv.customer_window_expires_at = _window_expires_at()
            conv.updated_at = _now()
            if contact_name and conv.contact_name != contact_name:
                conv.contact_name = contact_name
            db.commit()
            return conv

        now = _now()
        conv = Conversation(
            phone_number_id=phone_number_id,
            from_phone=from_phone,
            contact_name=contact_name,
            customer_window_expires_at=_window_expires_at(),
            created_at=now,
            updated_at=now,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv


class MessageRepository:
    def create(
        self,
        db: Session,
        conversation_id: int,
        wamid: str,
        message_type: str,
        direction: str,
        body: str | None = None,
        media_id: str | None = None,
        media_url: str | None = None,
        mime_type: str | None = None,
        raw_payload: dict | None = None,
    ) -> Message | None:
        """Insert a new message. Returns None if wamid already exists (idempotent)."""
        now = _now()
        msg = Message(
            conversation_id=conversation_id,
            wamid=wamid,
            message_type=message_type,
            direction=direction,
            body=body,
            media_id=media_id,
            media_url=media_url,
            mime_type=mime_type,
            status="sent" if direction == "outbound" else None,
            sent_at=now if direction == "outbound" else None,
            raw_payload=raw_payload,
            created_at=now,
            updated_at=now,
        )
        db.add(msg)
        try:
            db.commit()
            db.refresh(msg)
            return msg
        except IntegrityError:
            db.rollback()
            logger.debug("Duplicate wamid=%s — skipping (idempotent)", wamid)
            return None

    def update_status(
        self,
        db: Session,
        wamid: str,
        status: str,
        timestamp: str,
    ) -> None:
        msg = db.query(Message).filter_by(wamid=wamid).first()
        if not msg:
            return
        ts = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).replace(tzinfo=None)
        msg.status = status
        msg.updated_at = _now()
        if status == "delivered":
            msg.delivered_at = ts
        elif status == "read":
            msg.read_at = ts
        elif status == "failed":
            msg.failed_at = ts
        db.commit()


class AgentRunRepository:
    def create(
        self,
        db: Session,
        conversation_id: int,
        triggered_by_wamid: str,
        model_id: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cache_read_tokens: int | None = None,
        cache_write_tokens: int | None = None,
        latency_ms: int | None = None,
        error: str | None = None,
    ) -> AgentRun:
        run = AgentRun(
            conversation_id=conversation_id,
            triggered_by_wamid=triggered_by_wamid,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
            latency_ms=latency_ms,
            error=error,
            created_at=_now(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run


conversation_repo = ConversationRepository()
message_repo = MessageRepository()
agent_run_repo = AgentRunRepository()
