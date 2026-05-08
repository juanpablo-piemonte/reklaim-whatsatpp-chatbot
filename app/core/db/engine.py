import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        if not all([settings.db_host, settings.db_user, settings.db_pass, settings.db_name]):
            raise RuntimeError("DB credentials are not fully configured")

        ssl_args = {}
        if os.path.exists(settings.db_ssl_cert):
            ssl_args = {"ssl_ca": settings.db_ssl_cert}
        else:
            logger.warning("DB SSL cert not found at %s — connecting without SSL", settings.db_ssl_cert)

        query = "?ssl_ca=" + settings.db_ssl_cert if ssl_args else ""
        url = (
            f"mysql+pymysql://{settings.db_user}:{settings.db_pass}"
            f"@{settings.db_host}/{settings.db_name}{query}"
        )
        _engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
        logger.info("DB engine created: host=%s db=%s ssl=%s", settings.db_host, settings.db_name, bool(ssl_args))
    return _engine


def get_db():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Return True if the DB is reachable, False otherwise. Used by /health."""
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("DB health check failed: %s", exc)
        return False
