from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from app.config import get_settings
Base = declarative_base()

def create_db_engine(db_url: str | None=None) -> Engine:
    database_url = db_url or get_settings().database_url
    connect_args = {'check_same_thread': False} if database_url.startswith('sqlite') else {}
    return create_engine(database_url, connect_args=connect_args)
engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

def init_db() -> None:
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()