"""Customer ORM model."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_unique_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    customer_zip_code_prefix: Mapped[str | None] = mapped_column(String(16))
    customer_city: Mapped[str | None] = mapped_column(Text)
    customer_state: Mapped[str | None] = mapped_column(String(8))
