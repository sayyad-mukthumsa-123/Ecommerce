"""Basic database-backed checks for the Step 7 FastAPI implementation."""

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from backend.api.v1.analytics import (
    analytics_summary,
    category_performance,
    delivery,
    monthly_sales,
    rfm,
    transactions,
)
from backend.api.v1.catalog import list_products
from backend.api.v1.customers import get_customer, list_customers
from backend.api.v1.orders import get_order, list_orders
from backend.database import Base, SessionLocal
from backend.main import app
from backend.schemas.common import PageParams


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_database_tables_and_connection(db):
    expected_tables = {
        "customers",
        "orders",
        "order_items",
        "payments",
        "reviews",
        "products",
        "sellers",
        "category_translation",
        "geolocation",
    }
    assert expected_tables.issubset(Base.metadata.tables)
    assert db.execute(text("SELECT 1")).scalar_one() == 1


def test_catalog_customer_and_order_pages(db):
    assert list_products(db, PageParams(limit=2, offset=0), None, None).pagination.returned == 2
    customers = list_customers(db, PageParams(limit=2, offset=0), None, None)
    assert customers.pagination.total == 1208
    customer_unique_id = customers.items[0].customer_unique_id
    assert get_customer(customer_unique_id, db).metrics.order_count >= 1
    orders = list_orders(db, PageParams(limit=2, offset=0), None, None, None, None, "purchase_date", "desc")
    assert orders.pagination.total == 1208
    assert get_order(orders.items[0].order_id, db).order_id == orders.items[0].order_id


def test_analytics_outputs(db):
    summary = analytics_summary(db)
    assert summary.eligible_orders == 1208
    assert summary.unique_customers == 539
    assert summary.repeat_customers == 380
    assert monthly_sales(db, None, None)
    assert rfm(PageParams(limit=2, offset=0), None, None).pagination.total == 539
    assert delivery(PageParams(limit=2, offset=0), None, None).pagination.total == 1208
    assert category_performance(db, 10, "revenue")
    assert transactions(PageParams(limit=2, offset=0), None, None, None).pagination.total == 1208


def test_openapi_contains_all_step7_route_groups():
    paths = app.openapi()["paths"]
    expected_paths = {
        "/health",
        "/health/database",
        "/api/v1/customers",
        "/api/v1/customers/{customer_unique_id}",
        "/api/v1/customers/{customer_unique_id}/orders",
        "/api/v1/orders",
        "/api/v1/orders/{order_id}",
        "/api/v1/products",
        "/api/v1/products/{product_id}",
        "/api/v1/analytics/summary",
        "/api/v1/analytics/rfm",
    }
    assert expected_paths.issubset(paths)


def test_missing_order_raises_404(db):
    with pytest.raises(HTTPException) as error:
        get_order("missing-order-id", db)
    assert error.value.status_code == 404
