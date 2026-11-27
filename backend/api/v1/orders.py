"""Version 1 order routes using direct parameterized SQL."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...schemas.common import PageParams, PaginationMeta
from ...schemas.order import (
    OrderDetailResponse,
    OrderItemResponse,
    OrderSummaryResponse,
    PaginatedOrderResponse,
    PaymentResponse,
    ReviewResponse,
)
from ..deps import database_session


router = APIRouter(tags=["orders"])
DatabaseSession = Annotated[Session, Depends(database_session)]

ORDER_SUMMARY_SQL = """
    SELECT o.order_id, o.customer_id, c.customer_unique_id, o.order_status,
           o.order_purchase_timestamp, o.order_approved_at,
           o.order_delivered_carrier_date, o.order_delivered_customer_date,
           o.order_estimated_delivery_date,
           COALESCE(i.item_count, 0) AS item_count,
           COALESCE(i.item_revenue_brl, 0) AS item_revenue_brl,
           COALESCE(i.freight_collected_brl, 0) AS freight_collected_brl,
           COALESCE(p.payment_total_brl, 0) AS payment_total_brl
    FROM orders AS o
    INNER JOIN customers AS c ON c.customer_id = o.customer_id
    LEFT JOIN (
        SELECT order_id, COUNT(*) AS item_count,
               SUM(price) AS item_revenue_brl,
               SUM(freight_value) AS freight_collected_brl
        FROM order_items
        GROUP BY order_id
    ) AS i ON i.order_id = o.order_id
    LEFT JOIN (
        SELECT order_id, SUM(payment_value) AS payment_total_brl
        FROM payments
        GROUP BY order_id
    ) AS p ON p.order_id = o.order_id
"""


def _not_found(order_id: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order '{order_id}' was not found")


def _filters(
    *,
    order_status: str | None,
    customer_unique_id: str | None,
    start_date: date | None,
    end_date: date | None,
    params: dict[str, object],
) -> str:
    conditions: list[str] = []
    if order_status:
        conditions.append("o.order_status = :order_status")
        params["order_status"] = order_status
    if customer_unique_id:
        conditions.append("c.customer_unique_id = :customer_unique_id")
        params["customer_unique_id"] = customer_unique_id
    if start_date:
        conditions.append("o.order_purchase_timestamp >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("o.order_purchase_timestamp < DATE_ADD(:end_date, INTERVAL 1 DAY)")
        params["end_date"] = end_date
    return f"WHERE {' AND '.join(conditions)}" if conditions else ""


def _summary(row: object) -> OrderSummaryResponse:
    return OrderSummaryResponse.model_validate(row)


@router.get("/orders", response_model=PaginatedOrderResponse)
def list_orders(
    db: DatabaseSession,
    page: Annotated[PageParams, Depends()],
    order_status: str | None = Query(default=None, min_length=1),
    customer_unique_id: str | None = Query(default=None, min_length=1),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    sort_by: Literal["purchase_date", "total_value"] = Query(default="purchase_date"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
) -> PaginatedOrderResponse:
    """Return paginated orders with status, customer, date, and sorting filters."""
    params: dict[str, object] = {"limit": page.limit, "offset": page.offset}
    where_sql = _filters(
        order_status=order_status,
        customer_unique_id=customer_unique_id,
        start_date=start_date,
        end_date=end_date,
        params=params,
    )
    sort_expression = (
        "o.order_purchase_timestamp" if sort_by == "purchase_date" else
        "(COALESCE(i.item_revenue_brl, 0) + COALESCE(i.freight_collected_brl, 0))"
    )
    direction = "ASC" if sort_order == "asc" else "DESC"
    rows = db.execute(
        text(
            f"""{ORDER_SUMMARY_SQL}
            {where_sql}
            ORDER BY {sort_expression} {direction}, o.order_id
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    items = [_summary(row) for row in rows]
    count_params = {key: value for key, value in params.items() if key not in {"limit", "offset"}}
    total = int(
        db.execute(
            text(f"SELECT COUNT(*) FROM orders AS o INNER JOIN customers AS c ON c.customer_id = o.customer_id {where_sql}"),
            count_params,
        ).scalar_one()
    )
    return PaginatedOrderResponse(
        items=items,
        pagination=PaginationMeta(total=total, limit=page.limit, offset=page.offset, returned=len(items)),
    )


@router.get("/orders/{order_id}", response_model=OrderDetailResponse)
def get_order(order_id: str, db: DatabaseSession) -> OrderDetailResponse:
    """Return an order with separately queried items, payments, and reviews."""
    row = db.execute(
        text(f"{ORDER_SUMMARY_SQL} WHERE o.order_id = :order_id"),
        {"order_id": order_id},
    ).mappings().first()
    if row is None:
        raise _not_found(order_id)

    items = [
        OrderItemResponse.model_validate(item)
        for item in db.execute(
            text(
                """
                SELECT order_id, order_item_id, product_id, seller_id,
                       shipping_limit_date, price AS price_brl,
                       freight_value AS freight_value_brl
                FROM order_items
                WHERE order_id = :order_id
                ORDER BY order_item_id
                """
            ),
            {"order_id": order_id},
        ).mappings().all()
    ]
    payments = [
        PaymentResponse.model_validate(payment)
        for payment in db.execute(
            text(
                """
                SELECT order_id, payment_sequential, payment_type,
                       payment_installments, payment_value AS payment_value_brl
                FROM payments
                WHERE order_id = :order_id
                ORDER BY payment_sequential
                """
            ),
            {"order_id": order_id},
        ).mappings().all()
    ]
    reviews = [
        ReviewResponse.model_validate(review)
        for review in db.execute(
            text(
                """
                SELECT review_id, order_id, review_score,
                       review_comment_title, review_comment_message,
                       review_creation_date, review_answer_timestamp
                FROM reviews
                WHERE order_id = :order_id
                ORDER BY review_record_id
                """
            ),
            {"order_id": order_id},
        ).mappings().all()
    ]
    return OrderDetailResponse(**_summary(row).model_dump(), items=items, payments=payments, reviews=reviews)
