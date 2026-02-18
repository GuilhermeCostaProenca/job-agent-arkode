from collections.abc import Generator

from sqlmodel import Session

from src.tracker.db import get_engine


def get_db_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
