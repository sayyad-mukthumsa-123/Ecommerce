"""Version 1 customer routes using direct parameterized SQL."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...schemas.common import PageParams, PaginationMeta
from ...schemas.customer import CustomerDetailResponse, CustomerMetrics, CustomerSummaryResponse, PaginatedCustomerResponse
from ...schemas.order import PaginatedOrderResponse
from ..deps import database_session
from .orders import list_orders


router = APIRouter(tags=["customers"])
DatabaseSession = Annotated[Session, Depends(database_session)]


@router.get("/customers", response_model=PaginatedCustomerResponse)
def list_customers(
    db: DatabaseSession,
    page: Annotated[PageParams, Depends()],
    customer_unique_id: str | None = Query(default=None, min_length=1),
    zip_code_prefix: str | None = Query(default=None, min_length=1),
) -> PaginatedCustomerResponse:
    """Return paginated customer records with optional identity/location filters."""
    conditions: list[str] = []
    params: dict[str, object] = {"limit": page.limit, "offset": page.offset}
    if customer_unique_id:
        conditions.append("customer_unique_id = :customer_unique_id")
        params["customer_unique_id"] = customer_unique_id
    if zip_code_prefix:
        conditions.append("customer_zip_code_prefix = :zip_code_prefix")
        params["zip_code_prefix"] = zip_code_prefix
    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        text(
            f"""
            SELECT customer_unique_id, customer_id, customer_zip_code_prefix,
                   customer_city, customer_state
            FROM customers
            {where_sql}
            ORDER BY customer_unique_id, customer_id
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    items = [CustomerSummaryResponse.model_validate(row) for row in rows]
    count_params = {key: value for key, value in params.items() if key not in {"limit", "offset"}}
    total = int(db.execute(text(f"SELECT COUNT(*) FROM customers {where_sql}"), count_params).scalar_one())
    return PaginatedCustomerResponse(
        items=items,
        pagination=PaginationMeta(total=total, limit=page.limit, offset=page.offset, returned=len(items)),
    )


@router.get("/customers/{customer_unique_id}", response_model=CustomerDetailResponse)
def get_customer(customer_unique_id: str, db: DatabaseSession) -> CustomerDetailResponse:
    """Return all customer records and delivered-order metrics for one person."""
    records = db.execute(
        text(
            """
            SELECT customer_unique_id, customer_id, customer_zip_code_prefix,
                   customer_city, customer_state
            FROM customers
            WHERE customer_unique_id = :customer_unique_id
            ORDER BY customer_id
            """
        ),
        {"customer_unique_id": customer_unique_id},
    ).mappings().all()
    if not records:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer '{customer_unique_id}' was not found")

    order_metrics = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT o.order_id) AS order_count,
                   MIN(o.order_purchase_timestamp) AS first_purchase_at,
                   MAX(o.order_purchase_timestamp) AS last_purchase_at
            FROM orders AS o
            INNER JOIN customers AS c ON c.customer_id = o.customer_id
            WHERE c.customer_unique_id = :customer_unique_id
              AND o.order_status = 'delivered'
            """
        ),
        {"customer_unique_id": customer_unique_id},
    ).mappings().one()
    item_metrics = db.execute(
        text(
            """
            SELECT COUNT(*) AS item_count,
                   COALESCE(SUM(oi.price), 0) AS item_revenue_brl,
                   COALESCE(SUM(oi.freight_value), 0) AS freight_collected_brl
            FROM order_items AS oi
            INNER JOIN orders AS o ON o.order_id = oi.order_id
            INNER JOIN customers AS c ON c.customer_id = o.customer_id
            WHERE c.customer_unique_id = :customer_unique_id
              AND o.order_status = 'delivered'
            """
        ),
        {"customer_unique_id": customer_unique_id},
    ).mappings().one()
    payment_metrics = db.execute(
        text(
            """
            SELECT COALESCE(SUM(p.payment_value), 0) AS payment_total_brl
            FROM payments AS p
            INNER JOIN orders AS o ON o.order_id = p.order_id
            INNER JOIN customers AS c ON c.customer_id = o.customer_id
            WHERE c.customer_unique_id = :customer_unique_id
              AND o.order_status = 'delivered'
            """
        ),
        {"customer_unique_id": customer_unique_id},
    ).mappings().one()
    first_purchase = order_metrics["first_purchase_at"]
    last_purchase = order_metrics["last_purchase_at"]
    recency_days = (date(2018, 8, 28) - last_purchase.date()).days if last_purchase else None
    metrics = CustomerMetrics(
        order_count=int(order_metrics["order_count"] or 0),
        item_count=int(item_metrics["item_count"] or 0),
        item_revenue_brl=item_metrics["item_revenue_brl"] or 0,
        freight_collected_brl=item_metrics["freight_collected_brl"] or 0,
        payment_total_brl=payment_metrics["payment_total_brl"] or 0,
        first_purchase_at=first_purchase,
        last_purchase_at=last_purchase,
        recency_days=max(recency_days, 0) if recency_days is not None else None,
        is_repeat_customer=int(order_metrics["order_count"] or 0) > 1,
    )
    return CustomerDetailResponse(
        customer_unique_id=customer_unique_id,
        customer_records=[CustomerSummaryResponse.model_validate(row) for row in records],
        metrics=metrics,
    )


@router.get("/customers/{customer_unique_id}/orders", response_model=PaginatedOrderResponse)
def list_customer_orders(
    customer_unique_id: str,
    db: DatabaseSession,
    page: Annotated[PageParams, Depends()],
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> PaginatedOrderResponse:
    """Return orders belonging to one person-level customer key."""
    return list_orders(
        db,
        page,
        order_status=None,
        customer_unique_id=customer_unique_id,
        start_date=start_date,
        end_date=end_date,
        sort_by="purchase_date",
        sort_order="desc",
    )
