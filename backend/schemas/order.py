"""Order API response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from .common import APIModel, PaginationMeta


def _clean_identifier(value: object) -> object:
    """Trim and validate non-empty identifiers."""
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError("identifier cannot be empty")
    return value


class OrderSummaryResponse(APIModel):
    order_id: str = Field(min_length=1, max_length=64)
    customer_id: str = Field(min_length=1, max_length=64)
    customer_unique_id: str = Field(min_length=1, max_length=64)
    order_status: str = Field(min_length=1, max_length=32)
    order_purchase_timestamp: datetime
    order_approved_at: datetime | None = None
    order_delivered_carrier_date: datetime | None = None
    order_delivered_customer_date: datetime | None = None
    order_estimated_delivery_date: datetime | None = None
    item_count: int = Field(ge=0)
    item_revenue_brl: Decimal = Field(ge=0)
    freight_collected_brl: Decimal = Field(ge=0)
    payment_total_brl: Decimal = Field(ge=0)

    _clean_ids = field_validator("order_id", "customer_id", "customer_unique_id", mode="before")(_clean_identifier)

    @model_validator(mode="after")
    def validate_order_dates(self):
        """Prevent milestone timestamps from preceding order purchase."""
        for timestamp in (
            self.order_approved_at,
            self.order_delivered_carrier_date,
            self.order_delivered_customer_date,
        ):
            if timestamp and timestamp < self.order_purchase_timestamp:
                raise ValueError("order milestone dates cannot precede order_purchase_timestamp")
        return self


class OrderItemResponse(APIModel):
    order_id: str = Field(min_length=1, max_length=64)
    order_item_id: int = Field(ge=1)
    product_id: str = Field(min_length=1, max_length=64)
    seller_id: str = Field(min_length=1, max_length=64)
    shipping_limit_date: datetime | None = None
    price_brl: Decimal = Field(ge=0)
    freight_value_brl: Decimal = Field(ge=0)

    _clean_ids = field_validator("order_id", "product_id", "seller_id", mode="before")(_clean_identifier)


class PaymentResponse(APIModel):
    order_id: str = Field(min_length=1, max_length=64)
    payment_sequential: int = Field(ge=1)
    payment_type: str = Field(min_length=1, max_length=32)
    payment_installments: int = Field(ge=1)
    payment_value_brl: Decimal = Field(ge=0)

    _clean_id = field_validator("order_id", mode="before")(_clean_identifier)


class ReviewResponse(APIModel):
    review_id: str | None = Field(default=None, min_length=1, max_length=64)
    order_id: str = Field(min_length=1, max_length=64)
    review_score: int = Field(ge=1, le=5)
    review_comment_title: str | None = None
    review_comment_message: str | None = None
    review_creation_date: datetime | None = None
    review_answer_timestamp: datetime | None = None

    _clean_ids = field_validator("review_id", "order_id", mode="before")(_clean_identifier)


class OrderDetailResponse(OrderSummaryResponse):
    items: list[OrderItemResponse]
    payments: list[PaymentResponse]
    reviews: list[ReviewResponse]

    @model_validator(mode="after")
    def validate_nested_order_ids(self):
        """Ensure all nested records belong to the detail response order."""
        nested_ids = [item.order_id for item in self.items]
        nested_ids.extend(payment.order_id for payment in self.payments)
        nested_ids.extend(review.order_id for review in self.reviews)
        if any(order_id != self.order_id for order_id in nested_ids):
            raise ValueError("nested order records must use the parent order_id")
        return self


class PaginatedOrderResponse(APIModel):
    items: list[OrderSummaryResponse]
    pagination: PaginationMeta

    @model_validator(mode="after")
    def validate_page_size(self):
        """Ensure pagination metadata describes the returned orders."""
        if self.pagination.returned != len(self.items):
            raise ValueError("pagination.returned must equal the number of items")
        return self
