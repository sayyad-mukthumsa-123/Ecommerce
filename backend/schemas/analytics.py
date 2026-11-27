"""Analytics API response schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .common import APIModel, PaginationMeta


class HealthResponse(APIModel):
    status: Literal["ok"]
    service: str
    version: str


class DatabaseHealthResponse(APIModel):
    status: Literal["ok", "unavailable"]
    database: str
    latency_ms: float = Field(ge=0)


class AnalyticsSummaryResponse(APIModel):
    eligible_orders: int = Field(ge=0)
    unique_customers: int = Field(ge=0)
    repeat_customers: int = Field(ge=0)
    item_revenue_brl: Decimal = Field(ge=0)
    freight_collected_brl: Decimal = Field(ge=0)
    payment_total_brl: Decimal = Field(ge=0)
    observation_start: date | None = None
    observation_end: date | None = None

    @model_validator(mode="after")
    def validate_summary_counts_and_dates(self):
        """Keep aggregate counts and the observation period logically ordered."""
        if self.unique_customers > self.eligible_orders:
            raise ValueError("unique_customers cannot exceed eligible_orders")
        if self.repeat_customers > self.unique_customers:
            raise ValueError("repeat_customers cannot exceed unique_customers")
        if self.observation_start and self.observation_end and self.observation_start > self.observation_end:
            raise ValueError("observation_start must be on or before observation_end")
        return self


class MonthlySalesResponse(APIModel):
    purchase_month: date
    order_count: int = Field(ge=0)
    unique_customers: int = Field(ge=0)
    item_revenue_brl: Decimal = Field(ge=0)
    freight_collected_brl: Decimal = Field(ge=0)
    item_plus_freight_brl: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_monthly_total(self):
        """Ensure the combined metric is not below either component."""
        if self.item_plus_freight_brl < self.item_revenue_brl or self.item_plus_freight_brl < self.freight_collected_brl:
            raise ValueError("item_plus_freight_brl must include both component amounts")
        return self


class RFMResponse(APIModel):
    customer_unique_id: str = Field(min_length=1, max_length=64)
    last_purchase: datetime
    recency_days: int = Field(ge=0)
    frequency: int = Field(ge=1)
    monetary_brl: Decimal = Field(ge=0)
    r_score: int = Field(ge=1, le=4)
    f_score: int = Field(ge=1, le=4)
    m_score: int = Field(ge=1, le=4)
    rfm_score: int = Field(ge=3, le=12)
    segment: Literal["high_value", "regular", "developing", "needs_attention"]

    @field_validator("customer_unique_id", mode="before")
    @classmethod
    def strip_customer_id(cls, value: object) -> object:
        """Trim the customer identifier before validation."""
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_rfm_score(self):
        """Ensure the displayed RFM score equals its three component scores."""
        if self.rfm_score != self.r_score + self.f_score + self.m_score:
            raise ValueError("rfm_score must equal r_score + f_score + m_score")
        return self


class PaginatedRFMResponse(APIModel):
    items: list[RFMResponse]
    pagination: PaginationMeta

    @model_validator(mode="after")
    def validate_page_size(self):
        if self.pagination.returned != len(self.items):
            raise ValueError("pagination.returned must equal the number of items")
        return self


class CohortRetentionResponse(APIModel):
    cohort_month: date
    month_number: int = Field(ge=0)
    cohort_size: int = Field(ge=0)
    retained_customers: int = Field(ge=0)
    retention_rate: Decimal = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_retention_counts(self):
        """A cohort cannot retain more customers than it originally contained."""
        if self.retained_customers > self.cohort_size:
            raise ValueError("retained_customers cannot exceed cohort_size")
        return self


class DeliveryMetricResponse(APIModel):
    order_id: str = Field(min_length=1, max_length=64)
    order_purchase_timestamp: datetime
    order_delivered_customer_date: datetime | None = None
    delivery_days: float | None = Field(default=None, ge=0)

    _clean_id = field_validator("order_id", mode="before")(
        lambda value: value.strip() if isinstance(value, str) and value.strip() else value
    )

    @model_validator(mode="after")
    def validate_delivery_date(self):
        """Ensure completed delivery cannot precede purchase."""
        if self.order_delivered_customer_date and self.order_delivered_customer_date < self.order_purchase_timestamp:
            raise ValueError("delivery date cannot precede purchase timestamp")
        return self


class PaginatedDeliveryMetricResponse(APIModel):
    items: list[DeliveryMetricResponse]
    pagination: PaginationMeta

    @model_validator(mode="after")
    def validate_page_size(self):
        if self.pagination.returned != len(self.items):
            raise ValueError("pagination.returned must equal the number of items")
        return self


class CategoryPerformanceResponse(APIModel):
    category_name: str = Field(min_length=1, max_length=255)
    item_count: int = Field(ge=0)
    item_revenue_brl: Decimal = Field(ge=0)

    @field_validator("category_name", mode="before")
    @classmethod
    def strip_category_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CLVTransactionResponse(APIModel):
    customer_unique_id: str = Field(min_length=1, max_length=64)
    order_id: str = Field(min_length=1, max_length=64)
    transaction_date: datetime
    monetary_value_brl: Decimal = Field(ge=0)

    @field_validator("customer_unique_id", "order_id", mode="before")
    @classmethod
    def strip_identifiers(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PaginatedCLVTransactionResponse(APIModel):
    items: list[CLVTransactionResponse]
    pagination: PaginationMeta

    @model_validator(mode="after")
    def validate_page_size(self):
        if self.pagination.returned != len(self.items):
            raise ValueError("pagination.returned must equal the number of items")
        return self
