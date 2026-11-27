"""Database engine, sessions, and FastAPI database dependency."""

import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Import Base and every model module explicitly. The models directory is a
# namespace package without an __init__.py, so explicit imports are required
# to register all tables in Base.metadata.
from .models.base import Base
from .models.category_translation import CategoryTranslation
from .models.customer import Customer
from .models.geolocation import Geolocation
from .models.order import Order
from .models.order_items import OrderItem
from .models.payment import Payment
from .models.product import Product
from .models.review import Review
from .models.seller import Seller


# Load DATABASE_URL from the project .env file.
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL in .env or in the environment.")


# One engine and one session factory are shared by the application.
engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Yield one database session per request and always close it."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """Run a minimal database health check without exposing connection details."""

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True

