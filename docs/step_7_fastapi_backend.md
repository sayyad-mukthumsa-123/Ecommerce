# Step 7 — FastAPI Backend: Current Implementation Reference

**Updated:** 27 November 2026  
**Status:** Implemented local read-only API, verified against the loaded MySQL database and Step 6 analytical extracts.

This document describes the implementation in [`backend/`](../backend/). It is the current reference, not the earlier proposed architecture. The application exposes catalog, customer, order, and analytics read operations. It does not import CSV files, mutate MySQL, train predictive CLV, or refresh Power BI.

## 1. Architecture

```text
Browser / Power BI / API client
              |
              v
FastAPI: backend/main.py
              |
  routers under backend/api/v1/
       |                    |
       v                    v
SQLAlchemy/MySQL      data/analytics/*.csv
       |
       v
ecommerce database (9 mapped tables)
```

[`main.py`](../backend/main.py) creates the app, middleware, error handlers, health checks, and `/api/v1` routers. [`database.py`](../backend/database.py) creates the SQLAlchemy engine/session from `DATABASE_URL`. Routers validate parameters, execute parameterized SQL or read controlled Step 6 CSV extracts, and return Pydantic response models.

The current implementation intentionally has no repository or service layer: SQL and response conversion are kept in the route modules for this small read-only API.

## 2. Folder and file structure

```text
backend/
├── main.py
├── database.py
├── api/
│   ├── deps.py
│   └── v1/
│       ├── analytics.py
│       ├── catalog.py
│       ├── customers.py
│       └── orders.py
├── models/
│   ├── base.py
│   ├── category_translation.py
│   ├── customer.py
│   ├── geolocation.py
│   ├── order.py
│   ├── order_items.py
│   ├── payment.py
│   ├── product.py
│   ├── review.py
│   └── seller.py
└── schemas/
    ├── analytics.py
    ├── catalog.py
    ├── common.py
    ├── customer.py
    └── order.py
```

`__pycache__/` folders and `.pyc` files are generated Python runtime artifacts, not source components.

### [`main.py`](../backend/main.py)

Creates the `FastAPI` application titled `Olist E-commerce Analytics API`, version `1.0.0`, and registers all four routers under `/api/v1`. It configures GET-only CORS from `ALLOWED_ORIGINS`, with local defaults, and adds security headers: `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`.

It defines `/`, `/health`, and `/health/database`. `/health` checks MySQL before returning `ok`; `/health/database` returns status and measured query latency. Shared handlers convert HTTP, validation, SQLAlchemy, and unexpected errors into the common error response. The app currently hardcodes its title/version rather than reading `APP_NAME`/`APP_VERSION` from `.env`.

### [`database.py`](../backend/database.py)

Loads `DATABASE_URL`, creates the SQLAlchemy engine with `pool_pre_ping=True` and `pool_recycle=1800`, creates `SessionLocal`, exposes the declarative `Base`, provides `get_db()` for short-lived sessions, and implements the `SELECT 1` connectivity check. It does not create or migrate tables automatically.

### [`api/deps.py`](../backend/api/deps.py)

Contains reusable API dependency support. The database session factory itself remains in [`database.py`](../backend/database.py).

## 3. API route modules

### [`api/v1/catalog.py`](../backend/api/v1/catalog.py)

Read-only product, seller, translation, and geolocation lookups:

- `GET /api/v1/products` and `/api/v1/products/{product_id}`
- `GET /api/v1/sellers` and `/api/v1/sellers/{seller_id}`
- `GET /api/v1/category-translations` and `/api/v1/category-translations/{product_category_name}`
- `GET /api/v1/geolocation` and `/api/v1/geolocation/{zip_code_prefix}`

List routes use validated pagination and deterministic ordering; detail routes return `404` when no record exists.

### [`api/v1/customers.py`](../backend/api/v1/customers.py)

Provides `GET /api/v1/customers`, `GET /api/v1/customers/{customer_unique_id}`, and `GET /api/v1/customers/{customer_unique_id}/orders`. Person-level history uses `customer_unique_id`, not only the order-level `customer_id`. Detail responses include derived customer/order metrics.

### [`api/v1/orders.py`](../backend/api/v1/orders.py)

Provides `GET /api/v1/orders` and `GET /api/v1/orders/{order_id}`. Listing supports pagination, status/date filters, and sorting. Detail results load items, payments, and reviews separately so multi-grain joins do not inflate totals.

### [`api/v1/analytics.py`](../backend/api/v1/analytics.py)

Combines live MySQL summaries with verified Step 6 extracts:

| Endpoint | Source | Purpose |
| --- | --- | --- |
| `/api/v1/analytics/summary` | MySQL | Orders, customers, repeat customers, revenue, and review summary |
| `/api/v1/analytics/monthly-sales` | MySQL | Monthly orders/revenue |
| `/api/v1/analytics/categories` | MySQL | Category performance |
| `/api/v1/analytics/rfm` | `data/analytics/rfm_step6.csv` | RFM customers and segments |
| `/api/v1/analytics/cohorts` | `data/analytics/cohort_retention_step6.csv` | Cohort retention rows |
| `/api/v1/analytics/delivery` | `data/analytics/delivery_metrics_step6.csv` | Delivery metrics |
| `/api/v1/analytics/transactions` | `data/analytics/clv_transactions_step6.csv` | Descriptive customer transaction values |

Predictive CLV is not exposed. The transaction endpoint is not a forecast.

## 4. ORM models

The model files map the nine loaded MySQL tables and supply table metadata/column types for SQLAlchemy queries:

- [`models/base.py`](../backend/models/base.py): declarative base and metadata registration.
- [`models/customer.py`](../backend/models/customer.py): `customers`, including order-level and person-level customer IDs.
- [`models/order.py`](../backend/models/order.py): `orders`, status, lifecycle timestamps, and analysis/audit timestamp fields.
- [`models/order_items.py`](../backend/models/order_items.py): `order_items` at `(order_id, order_item_id)` grain, with product, seller, price, and freight.
- [`models/payment.py`](../backend/models/payment.py): `payments`, payment sequence/type/installments/value.
- [`models/review.py`](../backend/models/review.py): `reviews`, including `review_record_id`, source `review_id`, score, comments, and timestamps.
- [`models/product.py`](../backend/models/product.py): `products`, category, descriptive attributes, dimensions, weight, and audit fields.
- [`models/seller.py`](../backend/models/seller.py): `sellers` and location fields.
- [`models/category_translation.py`](../backend/models/category_translation.py): Portuguese-to-English category translation.
- [`models/geolocation.py`](../backend/models/geolocation.py): representative ZIP-prefix lookup records.

The source `review_id` is not treated as a sole key because it is repeated in the reduced subset.

## 5. Pydantic schemas

- [`schemas/common.py`](../backend/schemas/common.py): pagination parameters/results and shared error structures. Current page limit range is 1–100.
- [`schemas/catalog.py`](../backend/schemas/catalog.py): product, seller, translation, and geolocation responses.
- [`schemas/customer.py`](../backend/schemas/customer.py): customer list/detail/history responses and metrics.
- [`schemas/order.py`](../backend/schemas/order.py): order responses and nested item/payment/review responses.
- [`schemas/analytics.py`](../backend/schemas/analytics.py): health, summary, monthly/category, RFM, cohort, delivery, and transaction responses.

These schemas form the public API contract and drive OpenAPI documentation at `/docs` and `/redoc`.

## 6. Connection to data, SQL, and reports

The API reads MySQL tables loaded from [`data/prepared/`](../data/prepared/). Reusable RFM, cohort, delivery, and descriptive CLV endpoints read [`data/analytics/`](../data/analytics/). Those extracts are produced by [`Python/run_post_load_pipeline.py`](../Python/run_post_load_pipeline.py); the repeatable batch procedure is [`future_batch_data_runbook.md`](./future_batch_data_runbook.md).

Current reconciliation rules are:

- `customer_id` is order-level; `customer_unique_id` is person-level.
- The delivered-only current subset reconciles to 1,208 orders, 539 people, and 380 repeat customers.
- Item revenue, freight, and payment totals remain separate measures.
- RFM/cohort results describe a repeat-customer-prioritized subset, not the full Olist population.

## 7. Run commands

From the project root, with the project `.env` configured:

```powershell
& .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Alternatively activate the environment first:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn backend.main:app --reload
```

The MySQL `ecommerce` database and all nine tables must already exist. Useful URLs are `http://127.0.0.1:8000/docs`, `http://127.0.0.1:8000/redoc`, and `http://127.0.0.1:8000/health`.

## 8. Verification

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/test_backend_basic.py -q
```

[`tests/test_backend_basic.py`](../tests/test_backend_basic.py) directly calls route functions and verifies MySQL connectivity, nine mapped tables, catalog/customer/order routes, the current analytics reconciliation values, OpenAPI route registration, and a missing-order `404`. It is an integration-style check and requires the configured database and current analytics extracts.

## 9. Current limitations

Authentication/authorization, write/import endpoints, predictive CLV, model storage, async database access, migrations, production workers, and configurable analytics-file paths are not implemented. The API is complete for the current local analytics MVP; these are future extensions rather than missing prerequisites for the routes listed above.
