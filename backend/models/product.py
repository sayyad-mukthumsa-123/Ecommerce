"""Product ORM model."""

from sqlalchemy import Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(Text, primary_key=True)
    product_category_name: Mapped[str | None] = mapped_column(Text)
    product_name_lenght: Mapped[int | None] = mapped_column(Integer)
    product_description_lenght: Mapped[int | None] = mapped_column(Integer)
    product_photos_qty: Mapped[int | None] = mapped_column(Integer)
    product_weight_g: Mapped[float | None] = mapped_column(Float)
    product_length_cm: Mapped[float | None] = mapped_column(Float)
    product_height_cm: Mapped[float | None] = mapped_column(Float)
    product_width_cm: Mapped[float | None] = mapped_column(Float)
    product_attributes_optional_flag: Mapped[int | None] = mapped_column(Integer)
    product_attributes_imputed_flag: Mapped[int | None] = mapped_column(Integer)
    product_attributes_imputation_method: Mapped[str | None] = mapped_column(Text)
    product_category_missing_flag: Mapped[int | None] = mapped_column(Integer)
