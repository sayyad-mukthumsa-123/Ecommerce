"""Seller ORM model."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Seller(Base):
    __tablename__ = "sellers"

    seller_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    seller_zip_code_prefix: Mapped[str | None] = mapped_column(String(16))
    seller_city: Mapped[str | None] = mapped_column(Text)
    seller_state: Mapped[str | None] = mapped_column(String(8))
