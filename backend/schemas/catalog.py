"""Product, seller, category, and geolocation API schemas."""

from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from .common import APIModel, PaginationMeta


class ProductResponse(APIModel):
    product_id: str = Field(min_length=1, max_length=64)
    product_category_name: str | None = Field(default=None, min_length=1, max_length=255)
    product_category_name_english: str | None = Field(default=None, min_length=1, max_length=255)
    product_name_lenght: int | None = Field(default=None, ge=0)
    product_description_lenght: int | None = Field(default=None, ge=0)
    product_photos_qty: int | None = Field(default=None, ge=0)
    product_weight_g: Decimal | None = Field(default=None, ge=0)
    product_length_cm: Decimal | None = Field(default=None, ge=0)
    product_height_cm: Decimal | None = Field(default=None, ge=0)
    product_width_cm: Decimal | None = Field(default=None, ge=0)

    @field_validator("product_id", "product_category_name", "product_category_name_english", mode="before")
    @classmethod
    def strip_product_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PaginatedProductResponse(APIModel):
    items: list[ProductResponse]
    pagination: PaginationMeta

    @model_validator(mode="after")
    def validate_page_size(self):
        if self.pagination.returned != len(self.items):
            raise ValueError("pagination.returned must equal the number of items")
        return self


class SellerResponse(APIModel):
    seller_id: str = Field(min_length=1, max_length=64)
    seller_zip_code_prefix: str | None = Field(default=None, min_length=1, max_length=10)
    seller_city: str | None = Field(default=None, min_length=1, max_length=100)
    seller_state: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("seller_id", "seller_zip_code_prefix", "seller_city", mode="before")
    @classmethod
    def strip_seller_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PaginatedSellerResponse(APIModel):
    items: list[SellerResponse]
    pagination: PaginationMeta

    @model_validator(mode="after")
    def validate_page_size(self):
        if self.pagination.returned != len(self.items):
            raise ValueError("pagination.returned must equal the number of items")
        return self


class CategoryTranslationResponse(APIModel):
    product_category_name: str = Field(min_length=1, max_length=255)
    product_category_name_english: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("product_category_name", "product_category_name_english", mode="before")
    @classmethod
    def strip_category_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PaginatedCategoryTranslationResponse(APIModel):
    items: list[CategoryTranslationResponse]
    pagination: PaginationMeta

    @model_validator(mode="after")
    def validate_page_size(self):
        if self.pagination.returned != len(self.items):
            raise ValueError("pagination.returned must equal the number of items")
        return self


class GeolocationResponse(APIModel):
    geolocation_zip_code_prefix: str = Field(min_length=1, max_length=10)
    geolocation_lat: Decimal | None = Field(default=None, ge=-90, le=90)
    geolocation_lng: Decimal | None = Field(default=None, ge=-180, le=180)
    geolocation_city: str | None = Field(default=None, min_length=1, max_length=100)
    geolocation_state: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("geolocation_zip_code_prefix", "geolocation_city", mode="before")
    @classmethod
    def strip_geolocation_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_coordinate_pair(self):
        """Require latitude and longitude together when coordinates are supplied."""
        if (self.geolocation_lat is None) != (self.geolocation_lng is None):
            raise ValueError("geolocation_lat and geolocation_lng must be provided together")
        return self


class PaginatedGeolocationResponse(APIModel):
    items: list[GeolocationResponse]
    pagination: PaginationMeta

    @model_validator(mode="after")
    def validate_page_size(self):
        if self.pagination.returned != len(self.items):
            raise ValueError("pagination.returned must equal the number of items")
        return self
