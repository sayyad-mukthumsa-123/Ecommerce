"""Customer API response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from .common import APIModel, PaginationMeta


class CustomerSummaryResponse(APIModel):
    customer_unique_id: str = Field(min_length=1, max_length=64)
    customer_id: str = Field(min_length=1, max_length=64)
    customer_zip_code_prefix: str | None = Field(default=None, min_length=1, max_length=10)
    customer_city: str | None = Field(default=None, min_length=1, max_length=100)
    customer_state: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("customer_unique_id", "customer_id", "customer_city", mode="before")
    @classmethod
    def strip_text_fields(cls, value: object) -> object:
        """Trim identifiers and optional city names before length validation."""
        return value.strip() if isinstance(value, str) else value


class CustomerMetrics(APIModel):
    order_count: int = Field(ge=0)
    item_count: int = Field(ge=0)
    item_revenue_brl: Decimal = Field(ge=0)
    freight_collected_brl: Decimal = Field(ge=0)
    payment_total_brl: Decimal = Field(ge=0)
    first_purchase_at: datetime | None = None
    last_purchase_at: datetime | None = None
    recency_days: int | None = Field(default=None, ge=0)
    is_repeat_customer: bool

    @model_validator(mode="after")
    def validate_repeat_flag(self):
        """Keep the repeat-customer flag consistent with the order count."""
        if self.is_repeat_customer != (self.order_count > 1):
            raise ValueError("is_repeat_customer must match whether order_count is greater than one")
        return self


class CustomerDetailResponse(APIModel):
    customer_unique_id: str
    customer_records: list[CustomerSummaryResponse]
    metrics: CustomerMetrics


class PaginatedCustomerResponse(APIModel):
    items: list[CustomerSummaryResponse]
    pagination: PaginationMeta

    @model_validator(mode="after")
    def validate_page_size(self):
        """Ensure pagination metadata describes the returned customer rows."""
        if self.pagination.returned != len(self.items):
            raise ValueError("pagination.returned must equal the number of items")
        return self
