"""Run the simple post-MySQL pipeline for the existing Power BI setup.

The manual handoff is an append to the existing MySQL tables. This script then
validates those tables and regenerates the existing files in data/analytics.
It does not load data, change MySQL tables, or create Power BI views.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYTICS_DIR = PROJECT_ROOT / "data" / "analytics"
QUALITY_DIR = PROJECT_ROOT / "data" / "quality"

TABLES = {
    "orders": "orders",
    "customers": "customers",
    "items": "order_items",
    "payments": "payments",
    "reviews": "reviews",
    "products": "products",
    "sellers": "sellers",
    "categories": "category_translation",
}


def read_tables(database_url: str) -> dict[str, pd.DataFrame]:
    """Read the existing MySQL tables without modifying them."""

    engine = create_engine(database_url)
    try:
        return {
            name: pd.read_sql_table(table_name, engine)
            for name, table_name in TABLES.items()
        }
    finally:
        engine.dispose()


def validate_tables(tables: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Run small, fail-fast checks on the loaded MySQL data."""

    orders = tables["orders"]
    customers = tables["customers"]
    items = tables["items"]
    products = tables["products"]
    sellers = tables["sellers"]
    reviews = tables["reviews"]

    checks = {
        "orders_rows": len(orders),
        "customers_rows": len(customers),
        "items_rows": len(items),
        "payments_rows": len(tables["payments"]),
        "reviews_rows": len(reviews),
        "duplicate_order_ids": int(orders["order_id"].duplicated().sum()),
        "orders_without_customers": int(
            (~orders["customer_id"].isin(customers["customer_id"])).sum()
        ),
        "items_without_orders": int(
            (~items["order_id"].isin(orders["order_id"])).sum()
        ),
        "items_without_products": int(
            (~items["product_id"].isin(products["product_id"])).sum()
        ),
        "items_without_sellers": int(
            (~items["seller_id"].isin(sellers["seller_id"])).sum()
        ),
        "invalid_review_scores": int(
            (~pd.to_numeric(reviews["review_score"], errors="coerce").between(1, 5)).sum()
        ),
    }

    failures = {
        name: value
        for name, value in checks.items()
        if name not in {"orders_rows", "customers_rows", "items_rows", "payments_rows", "reviews_rows"}
        and value
    }
    if failures:
        raise ValueError(f"Post-load validation failed: {failures}")
    return checks


def build_analytics(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Regenerate the existing analytics extracts from MySQL tables."""

    orders = tables["orders"].copy()
    customers = tables["customers"]
    items = tables["items"].copy()
    payments = tables["payments"].copy()

    date_columns = [column for column in orders if "date" in column or "timestamp" in column]
    for column in date_columns:
        orders[column] = pd.to_datetime(orders[column], errors="coerce")
    items["price"] = pd.to_numeric(items["price"], errors="coerce")
    items["freight_value"] = pd.to_numeric(items["freight_value"], errors="coerce")
    payments["payment_value"] = pd.to_numeric(payments["payment_value"], errors="coerce")

    eligible_orders = orders.loc[orders["order_status"].eq("delivered")].copy()
    item_summary = items.groupby("order_id", as_index=False).agg(
        item_count=("order_item_id", "count"),
        item_revenue=("price", "sum"),
        freight_collected=("freight_value", "sum"),
    )
    payment_summary = payments.groupby("order_id", as_index=False).agg(
        payment_total=("payment_value", "sum"),
        payment_count=("payment_sequential", "count"),
    )

    order_fact = (
        eligible_orders.merge(
            customers[["customer_id", "customer_unique_id"]],
            on="customer_id",
            how="left",
        )
        .merge(item_summary, on="order_id", how="left")
        .merge(payment_summary, on="order_id", how="left")
    )
    order_fact["item_plus_freight"] = (
        order_fact["item_revenue"] + order_fact["freight_collected"]
    )

    observation_cutoff = order_fact["order_purchase_timestamp"].max().normalize()
    rfm = order_fact.groupby("customer_unique_id", as_index=False).agg(
        last_purchase=("order_purchase_timestamp", "max"),
        frequency=("order_id", "nunique"),
        monetary=("item_plus_freight", "sum"),
    )
    rfm["recency_days"] = (
        observation_cutoff - rfm["last_purchase"].dt.normalize()
    ).dt.days
    rfm["monetary"] = rfm["monetary"].round(2)
    rfm["R_score"] = pd.qcut(
        rfm["recency_days"].rank(method="first"), 4, labels=[4, 3, 2, 1]
    ).astype(int)
    rfm["F_score"] = pd.qcut(
        rfm["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]
    ).astype(int)
    rfm["M_score"] = pd.qcut(
        rfm["monetary"].rank(method="first"), 4, labels=[1, 2, 3, 4]
    ).astype(int)
    rfm["RFM_score"] = rfm[["R_score", "F_score", "M_score"]].sum(axis=1)
    rfm["segment"] = np.select(
        [rfm["RFM_score"] >= 10, rfm["RFM_score"] >= 7, rfm["RFM_score"] <= 4],
        ["high_value", "regular", "needs_attention"],
        default="developing",
    )

    customer_orders = order_fact[["customer_unique_id", "order_purchase_timestamp"]].copy()
    customer_orders["purchase_month"] = customer_orders["order_purchase_timestamp"].dt.to_period("M")
    first_purchase = customer_orders.groupby("customer_unique_id")["purchase_month"].min()
    customer_orders["cohort_month"] = customer_orders["customer_unique_id"].map(first_purchase)
    customer_orders["month_number"] = (
        (customer_orders["purchase_month"].dt.year - customer_orders["cohort_month"].dt.year) * 12
        + customer_orders["purchase_month"].dt.month
        - customer_orders["cohort_month"].dt.month
    )
    cohort = customer_orders.groupby(["cohort_month", "month_number"])["customer_unique_id"].nunique().reset_index(name="retained_customers")
    cohort_sizes = cohort.loc[cohort["month_number"].eq(0), ["cohort_month", "retained_customers"]].rename(columns={"retained_customers": "cohort_size"})
    cohort = cohort.merge(cohort_sizes, on="cohort_month")
    cohort["retention_rate"] = (cohort["retained_customers"] / cohort["cohort_size"] * 100).round(2)

    delivery = eligible_orders[["order_id", "order_purchase_timestamp", "order_delivered_customer_date"]].copy()
    delivery["order_delivered_customer_date"] = pd.to_datetime(delivery["order_delivered_customer_date"], errors="coerce")
    delivery["delivery_days"] = (
        delivery["order_delivered_customer_date"] - delivery["order_purchase_timestamp"]
    ).dt.total_seconds().div(86400).round(2)

    clv = order_fact[["customer_unique_id", "order_id", "order_purchase_timestamp", "item_plus_freight"]].rename(
        columns={"order_purchase_timestamp": "transaction_date", "item_plus_freight": "monetary_value"}
    )
    clv["monetary_value"] = clv["monetary_value"].round(2)

    return {
        "order_fact_step6.csv": order_fact,
        "rfm_step6.csv": rfm,
        "cohort_retention_step6.csv": cohort,
        "delivery_metrics_step6.csv": delivery,
        "clv_transactions_step6.csv": clv,
    }


def save_outputs(outputs: dict[str, pd.DataFrame], checks: dict[str, int], batch_id: str) -> None:
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    for filename, dataframe in outputs.items():
        dataframe.to_csv(ANALYTICS_DIR / filename, index=False)

    pd.DataFrame([checks]).to_csv(QUALITY_DIR / "post_load_validation_summary.csv", index=False)
    run = {
        "batch_id": batch_id,
        "status": "success",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "analytics_files": sorted(outputs),
        "validation": checks,
    }
    (QUALITY_DIR / "post_load_pipeline_run.json").write_text(
        json.dumps(run, indent=2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run post-MySQL analytics refresh.")
    parser.add_argument("--batch-id", default=None, help="Optional manual MySQL batch identifier.")
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured in the project .env file")

    batch_id = args.batch_id or datetime.now(timezone.utc).strftime("batch-%Y%m%d-%H%M%S")
    try:
        tables = read_tables(database_url)
        checks = validate_tables(tables)
        outputs = build_analytics(tables)
        save_outputs(outputs, checks, batch_id)
    except Exception as exc:
        QUALITY_DIR.mkdir(parents=True, exist_ok=True)
        failure = {
            "batch_id": batch_id,
            "status": "failed",
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "error": str(exc),
        }
        (QUALITY_DIR / "post_load_pipeline_run.json").write_text(
            json.dumps(failure, indent=2), encoding="utf-8"
        )
        raise

    print(f"Post-load pipeline succeeded for {batch_id}")
    print(f"Updated analytics: {ANALYTICS_DIR}")
    print(f"Power BI can now be refreshed from its existing source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
