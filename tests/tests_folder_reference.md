# Tests Folder Reference

This document describes the complete current contents of the [tests/](../tests/) folder, including its maintained test module, generated cache files, fixtures, assertions, dependencies, execution commands, and coverage boundaries.

## 1. Folder contents

```text
tests/
├── test_backend_basic.py
└── __pycache__/
    ├── test_backend_basic.cpython-314.pyc
    └── test_backend_basic.cpython-314-pytest-9.2.0.pyc
```

The folder has one maintained pytest module. The `__pycache__/` files are generated Python bytecode and are not separate test implementations.

## 2. Purpose of the tests folder

The tests folder provides database-backed smoke and integration checks for the Step 7 FastAPI backend. The tests verify that:

- all nine SQLAlchemy table mappings are registered;
- the configured MySQL database is reachable;
- representative catalog, customer, and order reads work;
- the main analytics outputs are available and reconcile to the current snapshot;
- expected FastAPI route groups are registered in OpenAPI;
- a missing order produces a 404.

These are not isolated unit tests. They call real backend functions and use a real SQLAlchemy session connected through the project `DATABASE_URL`.

## 3. `test_backend_basic.py`

### What the file contains

The module contains imports, one reusable database fixture, and five test functions. It is intentionally small and focused on backend availability and current-data reconciliation.

### Why the file is needed

It catches failures at the most important integration boundaries: Python imports, ORM table registration, database connectivity, route/database behavior, analytical extract availability, OpenAPI registration, and not-found handling.

### Imports

- `pytest`: test runner, fixture decorator, and exception assertions.
- `HTTPException` from FastAPI: verifies the order-not-found contract.
- `text` from SQLAlchemy: executes `SELECT 1`.
- Analytics functions: `analytics_summary`, `category_performance`, `delivery`, `monthly_sales`, `rfm`, and `transactions`.
- Catalog function: `list_products`.
- Customer functions: `get_customer` and `list_customers`.
- Order functions: `get_order` and `list_orders`.
- `Base` and `SessionLocal` from `backend.database`: ORM metadata and real session factory.
- `app` from `backend.main`: OpenAPI route registry.
- `PageParams` from `backend.schemas.common`: validated pagination input.

## 4. `db` fixture

```python
@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

The fixture creates one SQLAlchemy session per test, yields it to the test, and closes it in a `finally` block. It prevents tests from leaking database connections while keeping session setup in one place.

It does not create a temporary database, load test records, or roll back a transaction. The tests therefore require the project MySQL database and current data to exist.

## 5. Test-by-test details

### `test_database_tables_and_connection(db)`

This test verifies the database layer before testing routes.

It requires these names in `Base.metadata.tables`:

- `customers`
- `orders`
- `order_items`
- `payments`
- `reviews`
- `products`
- `sellers`
- `category_translation`
- `geolocation`

Assertions:

1. `expected_tables.issubset(Base.metadata.tables)` confirms all nine ORM models are imported and mapped to the expected table names.
2. `db.execute(text("SELECT 1")).scalar_one() == 1` confirms the configured database session can execute SQL.

This catches missing model registration, invalid imports, a missing/incorrect `DATABASE_URL`, stopped MySQL, and invalid credentials.

### `test_catalog_customer_and_order_pages(db)`

This test checks representative list and detail operations.

Assertions:

1. `list_products(... PageParams(limit=2, offset=0) ...).pagination.returned == 2`
   - Confirms product pagination returns two rows for the first page.
2. `list_customers(...).pagination.total == 1208`
   - Confirms the current customer table contains 1,208 records according to the API query.
3. `get_customer(customer_unique_id, db).metrics.order_count >= 1`
   - Uses a real customer from the list response and verifies that customer detail metrics are available.
4. `list_orders(..., "purchase_date", "desc").pagination.total == 1208`
   - Confirms order pagination and purchase-date descending sorting work against the current 1,208-order snapshot.
5. `get_order(orders.items[0].order_id, db).order_id == orders.items[0].order_id`
   - Confirms a real listed order can be retrieved by ID and the detail response belongs to that order.

This test covers the basic catalog, customer, and order read path. It does not explicitly test seller, category-translation, or geolocation endpoints.

### `test_analytics_outputs(db)`

This test verifies the main analytics functions and the expected current analytical population.

Assertions:

| Assertion | What it verifies |
|---|---|
| `summary.eligible_orders == 1208` | Delivered/eligible order population. |
| `summary.unique_customers == 539` | Person-level customer count. |
| `summary.repeat_customers == 380` | Customers with more than one eligible order. |
| `monthly_sales(db, None, None)` is truthy | Monthly sales returns data without date filters. |
| `rfm(...).pagination.total == 539` | RFM extract has 539 customer rows. |
| `delivery(...).pagination.total == 1208` | Delivery extract has 1,208 rows. |
| `category_performance(db, 10, "revenue")` is truthy | Top-category query returns results ordered by revenue. |
| `transactions(...).pagination.total == 1208` | CLV transaction extract has 1,208 rows. |

This is important because the analytics route group combines live MySQL queries with CSV-backed Step 6 extracts. The test checks both sources at a high level.

It does not assert exact money totals, exact monthly values, category order, RFM component ranges, cohort values, delivery durations, or transaction amounts.

### `test_openapi_contains_all_step7_route_groups()`

This test calls `app.openapi()["paths"]` and requires these paths:

- `/health`
- `/health/database`
- `/api/v1/customers`
- `/api/v1/customers/{customer_unique_id}`
- `/api/v1/customers/{customer_unique_id}/orders`
- `/api/v1/orders`
- `/api/v1/orders/{order_id}`
- `/api/v1/products`
- `/api/v1/products/{product_id}`
- `/api/v1/analytics/summary`
- `/api/v1/analytics/rfm`

It catches missing router registration or incorrect `/api/v1` prefixes without requiring a live HTTP client. The assertion is a subset check, so it does not require every implemented path and does not inspect response schemas or query parameters.

### `test_missing_order_raises_404(db)`

This test calls `get_order("missing-order-id", db)` inside `pytest.raises(HTTPException)` and verifies `error.value.status_code == 404`.

It confirms that a missing order is represented as a not-found error instead of an empty or successful response. This protects client behavior and the API’s documented error contract.

## 6. Dataset assumptions encoded by the tests

Several assertions intentionally describe the current data snapshot:

| Expected value | Used by |
|---:|---|
| 1,208 customers | Customer pagination test. |
| 1,208 orders | Order pagination and delivery tests. |
| 539 unique people | Analytics summary and RFM tests. |
| 380 repeat customers | Analytics summary test. |
| 1,208 delivery rows | Delivery extract test. |
| 1,208 CLV transactions | Transaction extract test. |

When a future data batch changes these values, the tests can fail even when the backend is correct for the new data. Update these assertions deliberately as part of a documented dataset-version change.

## 7. Required environment and data

The tests require:

1. A Python environment with pytest and the project dependencies installed.
2. A project-root `.env` containing a valid connection, for example:

   ```text
   DATABASE_URL=mysql+pymysql://user:password@localhost:3306/ecommerce
   ```

3. A running MySQL server.
4. The `ecommerce` database with all nine expected tables.
5. The current selected dataset.
6. Current files under `data/analytics/` for RFM, delivery, and CLV tests.

The tests do not create the schema, import prepared CSVs, or generate analytics files. Run the data preparation and post-load pipeline first when validating a new batch.

## 8. Commands to run the tests

Run from the project root:

```powershell
cd C:\Users\mukth\OneDrive\Desktop\E-commerce
```

Run only this module:

```powershell
python -m pytest tests\test_backend_basic.py -q
```

Using the project virtual environment directly:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests\test_backend_basic.py -q
```

Run all discovered tests:

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
```

Run one test by name:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests\test_backend_basic.py -q -k test_analytics_outputs
```

## 9. Generated `__pycache__` files

### `test_backend_basic.cpython-314.pyc`

Python’s compiled bytecode cache for the test module.

### `test_backend_basic.cpython-314-pytest-9.2.0.pyc`

The compiled cache generated while pytest collects or executes the test module with the current Python/pytest versions.

These files contain generated bytecode, not independently maintained tests. They can be regenerated by importing or running the test module and should not be edited.

## 10. Current coverage boundaries

The smoke suite does not currently cover:

- seller, category-translation, and geolocation routes;
- invalid pagination and date-range inputs;
- unknown customer, product, seller, category, and geolocation 404 cases;
- exact shared error-response JSON shapes;
- CORS and security headers;
- every OpenAPI path and response model;
- all analytics filters;
- exact monetary reconciliation against every analytics CSV;
- cohort retention values and RFM score ranges;
- isolated temporary-database or transaction-rollback behavior.

These are suitable areas for future focused tests. A passing suite means the current smoke checks passed; it does not prove that every endpoint and error branch is covered.

## 11. Operating rules

- Run tests from the project root so `backend.main` and the namespace-package imports resolve correctly.
- Keep credentials in `.env`, never in test source.
- Treat hard-coded counts as current-snapshot controls and review them when data changes.
- Run post-load validation before testing a newly appended batch.
- Do not edit or commit generated `__pycache__` files.
