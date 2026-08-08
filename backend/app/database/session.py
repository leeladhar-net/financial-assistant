from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings
from app.database.base import Base

# Database engine initialization
database_url = settings.DATABASE_URL
connect_args = {}

if database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
