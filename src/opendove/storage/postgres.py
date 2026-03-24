from sqlalchemy import create_engine

from opendove.config import settings


def create_postgres_engine():
    return create_engine(settings.database_url, future=True)

