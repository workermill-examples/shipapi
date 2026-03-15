from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """Yield a database session per request. Override in tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()