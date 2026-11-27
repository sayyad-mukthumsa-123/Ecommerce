"""Order ORM model."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    order_status: Mapped[str | None] = mapped_column(String(32), index=True)
    order_purchase_timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    order_approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    order_delivered_carrier_date: Mapped[datetime | None] = mapped_column(DateTime)
    order_delivered_customer_date: Mapped[datetime | None] = mapped_column(DateTime)
    order_estimated_delivery_date: Mapped[datetime | None] = mapped_column(DateTime)
    source_order_approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    source_order_delivered_carrier_date: Mapped[datetime | None] = mapped_column(DateTime)
    source_order_delivered_customer_date: Mapped[datetime | None] = mapped_column(DateTime)
    date_correction_flag: Mapped[int | None] = mapped_column(Integer)
    date_correction_reason: Mapped[str | None] = mapped_column(Text)
    order_approved_at_missing_flag: Mapped[int | None] = mapped_column(Integer)
    order_approved_at_for_analysis: Mapped[datetime | None] = mapped_column(DateTime)
    order_approved_at_imputed_flag: Mapped[int | None] = mapped_column(Integer)
    order_approved_at_imputation_method: Mapped[str | None] = mapped_column(Text)
