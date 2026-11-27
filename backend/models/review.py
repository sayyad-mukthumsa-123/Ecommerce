"""Review ORM model."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Review(Base):
    __tablename__ = "reviews"

    # review_id is repeated in this dataset; review_record_id is the safe key.
    review_record_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[str | None] = mapped_column(String(64), index=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    review_score: Mapped[int | None] = mapped_column(Integer)
    review_comment_title: Mapped[str | None] = mapped_column(Text)
    review_comment_message: Mapped[str | None] = mapped_column(Text)
    review_creation_date: Mapped[datetime | None] = mapped_column(DateTime)
    review_answer_timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    review_comment_optional_flag: Mapped[int | None] = mapped_column(Integer)
    review_id_repeated_flag: Mapped[int | None] = mapped_column(Integer)
