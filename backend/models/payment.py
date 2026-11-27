"""Payment ORM model."""

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Payment(Base):
    __tablename__ = "payments"

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payment_sequential: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_type: Mapped[str | None] = mapped_column(String(32))
    payment_installments: Mapped[int | None] = mapped_column(Integer)
    payment_value: Mapped[float | None] = mapped_column(Float)
    payment_zero_value_flag: Mapped[int | None] = mapped_column(Integer)
