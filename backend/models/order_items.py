"""Order-item ORM model."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    seller_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    shipping_limit_date: Mapped[datetime | None] = mapped_column(DateTime)
    price: Mapped[float | None] = mapped_column(Float)
    freight_value: Mapped[float | None] = mapped_column(Float)
    freight_zero_value_flag: Mapped[int | None] = mapped_column(Integer)
