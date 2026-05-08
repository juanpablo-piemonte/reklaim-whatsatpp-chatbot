import logging

from app.whatsapp.models import Contact, PhoneMetadata

logger = logging.getLogger(__name__)


def get_or_create_conversation(
    phone_number_id: str,
    from_phone: str,
    contact: Contact | None,
):
    """Return (conversation, db) or (None, None) if DB is not configured."""
    try:
        from app.core.db.engine import get_db
        from app.core.db.repositories import conversation_repo
        db = next(get_db())
        contact_name = contact.profile.name if contact else None
        conv = conversation_repo.get_or_create(db, phone_number_id, from_phone, contact_name)
        return conv, db
    except RuntimeError:
        logger.debug("DB not configured — skipping conversation persistence")
        return None, None
    except Exception as exc:
        logger.warning("DB error in get_or_create_conversation: %s", exc)
        return None, None
