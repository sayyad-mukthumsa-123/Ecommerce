"""Version 1 analytical routes backed by SQL and Step 6 extracts."""

import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...schemas.analytics import (
    AnalyticsSummaryResponse,
    CategoryPerformanceResponse,
    CLVTransactionResponse,
    CohortRetentionResponse,
    DeliveryMetricResponse,
    MonthlySalesResponse,
    PaginatedCLVTransactionResponse,
    PaginatedDeliveryMetricResponse,
    PaginatedRFMResponse,
    RFMResponse,
)
from ...schemas.common import PageParams, PaginationMeta
from ..deps import database_session


router = APIRouter(prefix="/analytics", tags=["analytics"])
DatabaseSession = Annotated[Session, Depends(database_session)]
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "analytics"


def _read_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _page(items: list[object], page: PageParams) -> tuple[list[object], PaginationMeta]:
    selected = items[page.offset : page.offset + page.limit]
    return selected, PaginationMeta(total=len(items), limit=page.limit, offset=page.offset, returned=len(selected))


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def analytics_summary(db: DatabaseSession) -> AnalyticsSummaryResponse:
    """Return delivered-order counts and independently aggregated monetary totals."""
    counts = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT o.order_id) AS eligible_orders,
                   COUNT(DISTINCT c.customer_unique_id) AS unique_customers
            FROM orders AS o
            INNER JOIN customers AS c ON c.customer_id = o.customer_id
            WHERE o.order_status = 'delivered'
            """
        )
    ).mappings().one()
    repeat = db.execute(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT c.customer_unique_id
                FROM orders AS o
                INNER JOIN customers AS c ON c.customer_id = o.customer_id
                WHERE o.order_status = 'delivered'
                GROUP BY c.customer_unique_id
                HAVING COUNT(DISTINCT o.order_id) > 1
            ) AS repeat_customers
            """
        )
    ).scalar_one()
    item_totals = db.execute(
        text(
            """
            SELECT COALESCE(SUM(oi.price), 0) AS item_revenue_brl,
                   COALESCE(SUM(oi.freight_value), 0) AS freight_collected_brl
            FROM order_items AS oi
            INNER JOIN orders AS o ON o.order_id = oi.order_id
            WHERE o.order_status = 'delivered'
            """
        )
    ).mappings().one()
    payment_total = db.execute(
        text(
            """
            SELECT COALESCE(SUM(p.payment_value), 0)
            FROM payments AS p
            INNER JOIN orders AS o ON o.order_id = p.order_id
            WHERE o.order_status = 'delivered'
            """
        )
    ).scalar_one()
    dates = db.execute(
        text(
            """
            SELECT MIN(order_purchase_timestamp) AS observation_start,
                   MAX(order_purchase_timestamp) AS observation_end
            FROM orders
            WHERE order_status = 'delivered'
            """
        )
    ).mappings().one()
    return AnalyticsSummaryResponse(
        eligible_orders=int(counts["eligible_orders"] or 0),
        unique_customers=int(counts["unique_customers"] or 0),
        repeat_customers=int(repeat or 0),
        item_revenue_brl=item_totals["item_revenue_brl"] or 0,
        freight_collected_brl=item_totals["freight_collected_brl"] or 0,
        payment_total_brl=payment_total or 0,
        observation_start=dates["observation_start"].date() if dates["observation_start"] else None,
        observation_end=dates["observation_end"].date() if dates["observation_end"] else None,
    )


@router.get("/monthly-sales", response_model=list[MonthlySalesResponse])
def monthly_sales(
    db: DatabaseSession,
    start_month: date | None = Query(default=None),
    end_month: date | None = Query(default=None),
) -> list[MonthlySalesResponse]:
    """Return monthly delivered-order sales with separate item and freight totals."""
    conditions = ["o.order_status = 'delivered'"]
    params: dict[str, object] = {}
    if start_month:
        conditions.append("o.order_purchase_timestamp >= :start_month")
        params["start_month"] = start_month
    if end_month:
        conditions.append("o.order_purchase_timestamp < DATE_ADD(:end_month, INTERVAL 1 MONTH)")
        params["end_month"] = end_month
    rows = db.execute(
        text(
            f"""
            SELECT DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m-01') AS purchase_month,
                   COUNT(DISTINCT o.order_id) AS order_count,
                   COUNT(DISTINCT c.customer_unique_id) AS unique_customers,
                   COALESCE(SUM(oi.price), 0) AS item_revenue_brl,
                   COALESCE(SUM(oi.freight_value), 0) AS freight_collected_brl,
                   COALESCE(SUM(oi.price + oi.freight_value), 0) AS item_plus_freight_brl
            FROM orders AS o
            INNER JOIN customers AS c ON c.customer_id = o.customer_id
            INNER JOIN order_items AS oi ON oi.order_id = o.order_id
            WHERE {' AND '.join(conditions)}
            GROUP BY DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m-01')
            ORDER BY purchase_month
            """
        ),
        params,
    ).mappings().all()
    return [MonthlySalesResponse.model_validate(row) for row in rows]


@router.get("/rfm", response_model=PaginatedRFMResponse)
def rfm(
    page: Annotated[PageParams, Depends()],
    segment: Literal["high_value", "regular", "developing", "needs_attention"] | None = Query(default=None),
    min_score: int | None = Query(default=None, ge=1, le=12),
) -> PaginatedRFMResponse:
    """Return the Step 6 descriptive RFM extract with optional filters."""
    records = []
    for row in _read_csv("rfm_step6.csv"):
        records.append(
            RFMResponse(
                customer_unique_id=row["customer_unique_id"],
                last_purchase=datetime.fromisoformat(row["last_purchase"]),
                recency_days=int(row["recency_days"]),
                frequency=int(row["frequency"]),
                monetary_brl=Decimal(row["monetary"]),
                r_score=int(row["R_score"]),
                f_score=int(row["F_score"]),
                m_score=int(row["M_score"]),
                rfm_score=int(row["RFM_score"]),
                segment=row["segment"],
            )
        )
    if segment:
        records = [record for record in records if record.segment == segment]
    if min_score is not None:
        records = [record for record in records if record.rfm_score >= min_score]
    records.sort(key=lambda record: record.rfm_score, reverse=True)
    items, pagination = _page(records, page)
    return PaginatedRFMResponse(items=items, pagination=pagination)


@router.get("/cohorts", response_model=list[CohortRetentionResponse])
def cohorts(
    cohort_month: date | None = Query(default=None),
    max_month_number: int = Query(default=12, ge=0, le=36),
) -> list[CohortRetentionResponse]:
    """Return Step 6 cohort retention rows with optional filters."""
    records = []
    for row in _read_csv("cohort_retention_step6.csv"):
        month = date.fromisoformat(f"{row['cohort_month']}-01")
        if cohort_month and month != cohort_month.replace(day=1):
            continue
        if int(row["month_number"]) > max_month_number:
            continue
        records.append(
            CohortRetentionResponse(
                cohort_month=month,
                month_number=int(row["month_number"]),
                cohort_size=int(row["cohort_size"]),
                retained_customers=int(row["retained_customers"]),
                retention_rate=Decimal(row["retention_rate"]),
            )
        )
    return records


@router.get("/delivery", response_model=PaginatedDeliveryMetricResponse)
def delivery(
    page: Annotated[PageParams, Depends()],
    min_days: float | None = Query(default=None, ge=0),
    max_days: float | None = Query(default=None, ge=0),
) -> PaginatedDeliveryMetricResponse:
    """Return delivery metrics from the Step 6 analytical extract."""
    records = [
        DeliveryMetricResponse(
            order_id=row["order_id"],
            order_purchase_timestamp=datetime.fromisoformat(row["order_purchase_timestamp"]),
            order_delivered_customer_date=datetime.fromisoformat(row["order_delivered_customer_date"]),
            delivery_days=float(row["delivery_days"]),
        )
        for row in _read_csv("delivery_metrics_step6.csv")
    ]
    if min_days is not None:
        records = [record for record in records if record.delivery_days is not None and record.delivery_days >= min_days]
    if max_days is not None:
        records = [record for record in records if record.delivery_days is not None and record.delivery_days <= max_days]
    records.sort(key=lambda record: record.delivery_days or 0, reverse=True)
    items, pagination = _page(records, page)
    return PaginatedDeliveryMetricResponse(items=items, pagination=pagination)


@router.get("/categories", response_model=list[CategoryPerformanceResponse])
def category_performance(
    db: DatabaseSession,
    limit: int = Query(default=10, ge=1, le=100),
    order_by: Literal["revenue", "items"] = Query(default="revenue"),
) -> list[CategoryPerformanceResponse]:
    """Return top delivered categories by item revenue or item count."""
    ordering = "item_revenue_brl DESC" if order_by == "revenue" else "item_count DESC"
    rows = db.execute(
        text(
            f"""
            SELECT COALESCE(t.product_category_name_english,
                            p.product_category_name, 'unknown') AS category_name,
                   COUNT(*) AS item_count,
                   COALESCE(SUM(oi.price), 0) AS item_revenue_brl
            FROM order_items AS oi
            INNER JOIN orders AS o ON o.order_id = oi.order_id
            INNER JOIN products AS p ON p.product_id = oi.product_id
            LEFT JOIN category_translation AS t
              ON t.product_category_name = p.product_category_name
            WHERE o.order_status = 'delivered'
            GROUP BY COALESCE(t.product_category_name_english,
                              p.product_category_name, 'unknown')
            ORDER BY {ordering}, category_name
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()
    return [CategoryPerformanceResponse.model_validate(row) for row in rows]


@router.get("/transactions", response_model=PaginatedCLVTransactionResponse)
def transactions(
    page: Annotated[PageParams, Depends()],
    customer_unique_id: str | None = Query(default=None, min_length=1),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> PaginatedCLVTransactionResponse:
    """Return Step 6 transaction-grain CLV inputs, not predictive CLV."""
    records = [
        CLVTransactionResponse(
            customer_unique_id=row["customer_unique_id"],
            order_id=row["order_id"],
            transaction_date=datetime.fromisoformat(row["transaction_date"]),
            monetary_value_brl=Decimal(row["monetary_value"]),
        )
        for row in _read_csv("clv_transactions_step6.csv")
    ]
    if customer_unique_id:
        records = [record for record in records if record.customer_unique_id == customer_unique_id]
    if start_date:
        records = [record for record in records if record.transaction_date.date() >= start_date]
    if end_date:
        records = [record for record in records if record.transaction_date.date() <= end_date]
    records.sort(key=lambda record: record.transaction_date)
    items, pagination = _page(records, page)
    return PaginatedCLVTransactionResponse(items=items, pagination=pagination)
