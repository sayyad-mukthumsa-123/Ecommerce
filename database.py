import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL in .env or in the environment.")

# Create database engine
engine = create_engine(DATABASE_URL)

# Test database connection
with engine.connect() as connection:
    result = connection.execute(text("SELECT 1"))
    print("MySQL connected successfully")
