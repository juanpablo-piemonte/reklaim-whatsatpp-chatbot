from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        if not all([settings.db_host, settings.db_user, settings.db_pass, settings.db_name]):
            raise RuntimeError("DB credentials are not fully configured in .env")
        url = (
            f"mysql+pymysql://{settings.db_user}:{settings.db_pass}"
            f"@{settings.db_host}/{settings.db_name}"
            f"?ssl_ca=global-bundle.pem"
        )
        _engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
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
