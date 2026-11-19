import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL in .env or in the environment.")

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def check_database_connection() -> bool:
    """Run a minimal database health check without exposing connection details."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
