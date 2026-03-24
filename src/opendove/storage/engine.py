from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from opendove.config import settings as _settings


def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or _settings.database_url
    return create_engine(url, future=True, pool_pre_ping=True)


def make_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    engine = make_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
