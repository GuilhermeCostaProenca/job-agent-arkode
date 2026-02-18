from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from src.core.config import get_settings


def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, echo=False)


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(get_engine())
