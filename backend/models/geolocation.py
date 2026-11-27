"""Geolocation ORM model."""

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Geolocation(Base):
    __tablename__ = "geolocation"

    geolocation_zip_code_prefix: Mapped[str] = mapped_column(String(16), primary_key=True)
    geolocation_lat: Mapped[float | None] = mapped_column(Float)
    geolocation_lng: Mapped[float | None] = mapped_column(Float)
    geolocation_city: Mapped[str | None] = mapped_column(Text)
    geolocation_state: Mapped[str | None] = mapped_column(String(8))
