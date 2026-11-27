"""FastAPI dependencies shared by route modules."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from ..database import get_db


def database_session() -> Generator[Session, None, None]:
    """Expose the request-scoped SQLAlchemy session to route handlers."""
    yield from get_db()
