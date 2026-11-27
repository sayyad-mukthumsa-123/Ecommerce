"""Product category translation ORM model."""

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CategoryTranslation(Base):
    __tablename__ = "category_translation"

    product_category_name: Mapped[str] = mapped_column(Text, primary_key=True)
    product_category_name_english: Mapped[str | None] = mapped_column(Text)
