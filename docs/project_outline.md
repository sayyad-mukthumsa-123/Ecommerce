# Enterprise E-Commerce Cohort and Customer Lifetime Value Engine

**FastAPI + MySQL Project Requirements and Implementation Outline**

- Document type: Project Requirements Document (PRD) + Software Requirements Specification (SRS) + Implementation Outline
- Prepared: 16 November 2026
- Status: Planning; no implementation or test results are claimed
- Project focus: Python backend engineering, MySQL data management, e-commerce analytics, and eventual Power BI reporting
- Source distinction: The overall architecture and advanced modeling requirements come from the research reports and checklist shared in this conversation. Endpoint names, response formats, acceptance tests, implementation priorities, and sample code conventions below are proposed implementation decisions unless explicitly identified as research requirements. Verify them against your code and dataset before treating them as finalized.

## 1. Project overview

Build a FastAPI application backed by MySQL that loads the Olist Brazilian E-Commerce dataset, exposes consistent customer and order information through REST APIs, calculates repeat-purchase and cohort metrics, and eventually provides predicted Customer Lifetime Value (CLV). Power BI can consume analytical data for interactive retention dashboards.

### Business problem

- Transactional data is split across multiple related files/tables.
- The business needs to understand who purchased, who returned, and how purchase behavior changes over time.
- Historical spending alone does not establish future customer value; a predictive CLV component can estimate expected future purchases and monetary value, subject to model assumptions and validation.
- Operational API queries and complex analytical reports have different performance needs.

### Project goals

1. Import and validate nine related CSV datasets.
2. Design an accurate relational MySQL schema.
3. Build documented, paginated, validated FastAPI endpoints.
4. Provide customer profiles, order history, and analytical summaries.
5. Compute cohorts and retention using customer_unique_id as the person-level identifier.
6. Add RFM and probabilistic CLV modeling as an advanced phase.
7. Connect a Power BI star-schema reporting model as a later phase.

### Non-goals for the initial backend MVP

- A shopping website, cart, checkout, or live payment processing.
- Real-time ingestion from an actual marketplace; the dataset is historical.
- Guaranteed accurate churn labels or future revenue predictions.
- Authentication/authorization for actual consumer accounts until access requirements are defined.
- A production read replica, reverse proxy, and heavy load test as prerequisites to a working local API.

## 2. Dataset and actual reduced-file scope

Original source: Olist Brazilian E-Commerce Public Dataset. Original orders cover approximately 2016–2018.

Current working data: Olist_Ecommerce_1500_Relational_Subset.zip, generated earlier in this conversation from the uploaded original dataset. It has at most 1,500 rows per CSV, not 1,500 customers or orders in every table. Its README.txt states the subset prioritizes repeat purchasers, uses authentic source records, and has partial geolocation coverage.

| CSV file | Rows in current subset | Purpose |
| --- | --- | --- |
| olist_orders_dataset.csv | 1,244 | Orders, status, lifecycle timestamps |
| olist_customers_dataset.csv | 1,244 | Order-linked customer records and customer_unique_id |
| olist_order_items_dataset.csv | 1,500 | Line items, product, seller, price, freight |
| olist_order_payments_dataset.csv | 1,333 | Payment types, installments and values |
| olist_order_reviews_dataset.csv | 1,341 | Review scores and comments |
| olist_products_dataset.csv | 1,131 | Product attributes |
| olist_sellers_dataset.csv | 483 | Seller attributes |
| product_category_name_translation.csv | 56 | Portuguese-to-English category names |
| olist_geolocation_dataset.csv | 1,020 | ZIP-prefix geography; subset may lack coverage |

### Critical data rules

- customer_id identifies an order-linked customer record; customer_unique_id identifies a repeat customer across orders. Do not calculate repeat customers using customer_id alone.
- Order items are not uniquely identified by order_item_id alone; use the composite (order_id, order_item_id).
- Payments may contain multiple records per order; preserve (order_id, payment_sequential) as a candidate composite key after validation.
- Reviews can require a surrogate/composite key if review_id is not unique in the imported data; validate before choosing the database key.
- Geolocation ZIP prefixes can occur repeatedly in the original dataset; the current reduced file has been deduplicated by prefix. Avoid enforcing foreign keys from customers/sellers to geolocation unless missing coverage is resolved.
- Because this subset deliberately prioritizes repeat purchasers, retention percentages and CLV behavior will not represent the original Olist population. Treat them as educational subset results, not market estimates.
- With only 1,244 orders, probabilistic CLV models may have too little repeat-purchase information for reliable fitting; report convergence and holdout limitations honestly.

### Dataset validation before import

- [ ] Confirm filenames, encodings, headers, row counts, data types.
- [ ] Check nulls and duplicates.
- [ ] Check unique keys and candidate composite keys.
- [ ] Check that order/customer/item/payment/review relationships are valid.
- [ ] Check products/sellers referenced by order items exist.
- [ ] Check timestamps and status values.
- [ ] Identify cancellations, unavailable orders, missing delivery dates and refunds; document rules instead of silently replacing dates.
- [ ] Verify count of repeat-purchase customer_unique_id values using the actual CSVs.
- [ ] Preserve raw input files unchanged.

## 3. Technology stack

| Layer | Technologies | Responsibility |
| --- | --- | --- |
| Programming | Python 3.12+ | ETL, services, API, analytics |
| API | FastAPI, Uvicorn | REST endpoints and OpenAPI docs |
| Validation | Pydantic V2 | Request/response schemas and validation |
| Database | MySQL 8.0 | Persistent relational data |
| ORM / driver | SQLAlchemy 2.0, asyncmy | Async database access |
| Migrations | Alembic | Schema versioning |
| Data engineering | Pandas, NumPy | CSV cleaning, aggregation and features |
| CLV (advanced) | lifetimes | BG/NBD and Gamma-Gamma modeling, subject to compatibility checks |
| Reporting (later) | Power BI, DAX, Power Query | Retention and CLV dashboards |
| Deployment (later) | Docker, Docker Compose; optional reverse proxy | Reproducible service deployment |
| Load tests (later) | Locust | Concurrent-request testing |

Important: For this backend scope, FastAPI + MySQL + Pydantic + SQLAlchemy + Pandas are central. Power BI, predictive CLV, Docker and Locust can be phased in after the backend MVP. The research proposes async SQLAlchemy; it is not necessary to mix PyMySQL synchronous sessions with an asyncmy async engine.

## 4. High-level architecture

```text
Nine Olist CSV files (historical)
              |
              v
Python/Pandas validation + ETL
              |
              v
      MySQL 8.0 OLTP schema
              ^
              |
FastAPI -> Pydantic -> Services -> SQLAlchemy AsyncSession
   |                |
   |                +--> Cohort/RFM aggregation
   |                +--> Stored CLV predictions (later)
   v
REST JSON responses / Swagger UI
              |
              +--> Power BI / analytical star schema (later)
```

Separation of concerns: Routes handle HTTP; schemas validate inputs/outputs; services enforce business logic; repositories/data-access functions execute queries; models define database tables; ETL is a separate repeatable process.

## 5. Database requirements and relational outline

### Core operational tables

| Table | Suggested key | Important fields | Relationship |
| --- | --- | --- | --- |
| customers | customer_id | customer_unique_id, ZIP prefix, city, state | One customer record to many possible orders at the schema level |
| orders | order_id | customer_id, status, purchase/approval/delivery dates | FK to customers |
| order_items | (order_id, order_item_id) | product_id, seller_id, price, freight_value | FK to orders/products/sellers |
| products | product_id | category, dimensions, weight | Referenced by order_items |
| sellers | seller_id | ZIP prefix, city, state | Referenced by order_items |
| order_payments | (order_id, payment_sequential) | payment type, installments, payment value | FK to orders |
| order_reviews | validated unique/composite/surrogate key | review_id, order_id, review score, comment, timestamps | FK to orders |
| category_translations | Portuguese category name | English category name | Referenced by products, if applicable |
| geolocation | ZIP prefix in reduced dataset | latitude, longitude, city, state | Optional lookup; incomplete subset coverage |

Do not create a single massive join across order items and payments and then sum both monetary fields: multiple items × multiple payment rows can multiply values. Aggregate payments and items separately at order grain before joining.

### Proposed additional analytical tables

- customer_metrics: customer_unique_id, observation_end_date, order_count, first_purchase_date, last_purchase_date, frequency, recency, tenure, monetary_value, calculated_at.
- customer_clv_predictions: customer_unique_id, model_version, forecast_start, horizon_months, expected_purchases, expected_transaction_value, predicted_clv, generated_at, model_status.
- etl_runs: source file, start/end time, inserted/updated/rejected counts, status, error summary.

These are proposed tables; the original nine CSVs do not contain predictions.

### Database constraints and indexes

- [ ] Primary keys, foreign keys, NOT NULL only where justified by observed data.
- [ ] Unique/composite constraints verified against CSVs before migration.
- [ ] Index orders(customer_id, order_purchase_timestamp).
- [ ] Index customers(customer_unique_id).
- [ ] Index child tables by order_id.
- [ ] Use DECIMAL for stored money; do not rely on binary floats for financial totals.
- [ ] Use consistent MySQL utf8mb4 character set.
- [ ] Define a repeatable Alembic migration path and test rollback in development.

## 6. Functional requirements (FR)

| ID | Requirement | Priority | Acceptance criterion |
| --- | --- | --- | --- |
| FR-01 | Import all nine CSV files | MVP | All intended rows imported or documented as rejected; counts reconcile |
| FR-02 | Preserve relational integrity | MVP | FK/key validation passes; no unexpected orphan rows |
| FR-03 | Customer listing and lookup | MVP | Paginated list and lookup by customer_id or customer_unique_id |
| FR-04 | Order listing and lookup | MVP | Paginated orders; filter by status and date range |
| FR-05 | Order details | MVP | Order items and payment/review data returned without duplicate monetary totals |
| FR-06 | Customer purchase history | MVP | All orders for one customer_unique_id are returned in date order |
| FR-07 | Validation and consistent errors | MVP | Invalid limits/dates return 422; unknown IDs return 404 |
| FR-08 | Cohort summary | Phase 2 | Acquisition month and monthly repeat-purchase retention computed |
| FR-09 | RFM customer metrics | Phase 2 | Frequency, recency, tenure, monetary values available with defined units |
| FR-10 | CLV model training | Phase 3 | Training job records success/failure and model assumptions |
| FR-11 | CLV prediction retrieval | Phase 3 | API returns stored model output with horizon, version, and timestamp |
| FR-12 | Power BI reporting dataset | Phase 4 | Analytics export or views support star-schema consumption |

### Proposed API routes (not existing endpoints)

Base prefix: /api/v1

| Method | Route | Purpose | Example parameters |
| --- | --- | --- | --- |
| GET | /health | Service health | None |
| GET | /customers | List customer records | limit, offset, state |
| GET | /customers/{customer_id} | Single customer record | Path ID |
| GET | /customers/unique/{customer_unique_id}/orders | All orders for a person | limit, offset |
| GET | /orders | List orders | limit, offset, status, start_date, end_date |
| GET | /orders/{order_id} | Order summary | Path ID |
| GET | /orders/{order_id}/items | Line items | Path ID |
| GET | /analytics/overview | Aggregate business metrics | Optional date range |
| GET | /analytics/cohorts | Cohort retention data | start_month, end_month |
| GET | /analytics/customers/{customer_unique_id}/rfm | Customer RFM | Path ID |
| GET | /analytics/customers/{customer_unique_id}/clv | Stored CLV forecast | horizon_months |

Design choice: The research also names /api/v1/customers/predict-clv as a potential ML endpoint. Prefer precomputed CLV results for fast GET requests; use a separately authorized training job/administrative action for expensive model fitting.

### Pagination contract

Proposed request: `GET /api/v1/orders?limit=50&offset=0`

```json
{
  "items": [],
  "total": 1244,
  "limit": 50,
  "offset": 0
}
```

This is an example response shape. The actual items array will contain order objects and the total depends on filters and imported data.

- Default limit=50; minimum 1, maximum 100 (proposed).
- offset >= 0.
- Stable ordering such as purchase timestamp + order ID.
- total counts the filtered result set, not always all orders.
- Use selectinload for order-item collections to avoid N+1 queries.

### Validation and error handling

- Validate UUID-like/text identifiers according to actual Olist ID formats, not arbitrary numeric IDs.
- Validate date ranges (end_date >= start_date).
- Validate positive pagination limits and nonnegative offsets.
- Use standard HTTP status codes: 200 success, 404 missing record, 422 invalid input, 500 unexpected server error.
- Return clear messages without exposing database passwords or stack traces.
- Log failures with request context while avoiding unnecessary sensitive information.

## 7. Non-functional requirements (NFR)

| ID | Area | Requirement / validation |
| --- | --- | --- |
| NFR-01 | Maintainability | Split routes, schemas, models, services, repositories, ETL and tests |
| NFR-02 | Data integrity | Transactional imports; FK constraints; idempotent/restartable ETL |
| NFR-03 | API reliability | Proper database session lifecycle; rollback on failures |
| NFR-04 | Async I/O | Use create_async_engine, async_sessionmaker, AsyncSession with asyncmy |
| NFR-05 | Connection safety | Configure pool_pre_ping=True; tune pool limits for environment |
| NFR-06 | Query efficiency | Index lookups, pagination, eager-loading, avoid unnecessary joins |
| NFR-07 | Security | Secrets in .env (excluded from Git); restricted CORS origins; least-privilege DB credentials |
| NFR-08 | Observability | Structured logs, error tracking, health endpoint, ETL run summaries |
| NFR-09 | Testing | Unit, API integration, data reconciliation and negative tests |
| NFR-10 | Reproducibility | Dependency lock/versioning, README, migration scripts, optional Docker Compose |
| NFR-11 | Performance | Measure response times and throughput; do not assert fixed SLAs without measurements |
| NFR-12 | Analytics correctness | Stable observation cutoff, no future-data leakage, consistent order-status rules |

Async session note: Use a fresh AsyncSession per request/task; do not share a session concurrently. expire_on_commit=False is recommended for async ORM usage. CPU-heavy model fitting should run outside the request's event loop, for example in a batch job.

CORS note: CORS is a browser enforcement mechanism, not a substitute for authentication or authorization. The Power BI desktop/connector integration may not depend on browser CORS in the same way as a JavaScript frontend.

## 8. Analytics definitions and business rules

Define these before implementing SQL/DAX to prevent conflicting results:

1. Customer identity: customer_unique_id for person-level counts; customer_id for linking orders.
2. Eligible orders: Decide whether to include only delivered orders for revenue/retention or all non-canceled orders; document the decision. Suggested MVP: use delivered orders for realized sales and retention, but expose status-filtered operational order endpoints separately.
3. Revenue: Specify whether it means item price, item price + freight_value, or payment_value; do not mix definitions. Suggested metric names: item_revenue, freight_collected, order_payment_total.
4. Cohort: Calendar month of each person's first eligible purchase.
5. Month offset: Calendar-month difference between order month and cohort month.
6. Cohort size: Distinct eligible customers in acquisition month.
7. Retained in month N: Distinct customers from that cohort with an eligible purchase in month N.
8. Retention rate: retained_customers / cohort_size * 100; Month 0 should be 100% by definition.
9. Observation cutoff: Use the last eligible transaction date or a documented analysis date; never use today's date blindly for historical 2016–2018 data.
10. RFM model units: Use one time unit consistently (days/weeks/months); lifetimes' frequency means repeat purchases, not all purchases.

### Cohort calculation example (illustrative only)

| Cohort | Customers acquired | Month 0 | Month 1 | Month 2 |
| --- | --- | --- | --- | --- |
| 2017-01 | 100 | 100% | 20% | 12% |
| 2017-02 | 80 | 100% | 25% | 10% |

These numbers are examples, not computed from the user's subset.

## 9. CLV model requirements (advanced phase)

The research proposes a two-model probabilistic approach using lifetimes:

1. Build a transaction table keyed by customer_unique_id, eligible purchase date, and order-level monetary amount.
2. Summarize frequency (repeat transactions), recency (first-to-last purchase interval), T/tenure (first purchase to observation end), and monetary value (average repeat transaction value).
3. Fit BG/NBD to predict future purchase frequency and probability of continued activity.
4. Fit Gamma-Gamma to estimate average future transaction value for qualifying repeat customers.
5. Check the assumption that transaction frequency and monetary value are sufficiently independent; inspect correlation rather than assuming validity.
6. Exclude zero/non-positive monetary values from Gamma-Gamma training; exclude zero-repeat-purchase customers from its fitting subset.
7. Handle sparse data and model convergence; consider a penalizer, document any failure.
8. Combine expected transactions and expected value with a defined forecast horizon and optional discount rate.
9. Store model version, observation cutoff, horizon and generation timestamp with predictions.
10. Validate predictions against a chronological holdout where data suffices; calculate MAE/RMSE as appropriate and report limitations.

Critical limitation: The 1,500-row-cap subset was intentionally selected to favor repeat buyers. It is useful for exercising the code but may bias CLV estimates and provide inadequate training/holdout samples. If models fail to fit, complete the descriptive RFM and cohort MVP first; do not fabricate predictions.

Profit vs revenue: Olist price/payment data do not directly establish customer profit margins. Unless actual margin/cost data are supplied, label forecasts as revenue-based CLV, not lifetime profit.

## 10. Suggested codebase structure

```text
olist-ecommerce-engine/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── v1/
│   │       ├── customers.py
│   │       ├── orders.py
│   │       └── analytics.py
│   ├── core/
│   │   └── config.py
│   ├── db/
│   │   ├── database.py
│   │   └── base.py
│   ├── models/
│   │   ├── customer.py
│   │   ├── order.py
│   │   └── ...
│   ├── schemas/
│   │   ├── customer.py
│   │   ├── order.py
│   │   └── analytics.py
│   ├── repositories/
│   └── services/
│       ├── customer_service.py
│       ├── order_service.py
│       ├── cohort_service.py
│       └── clv_service.py
├── scripts/
│   ├── inspect_data.py
│   ├── import_csv.py
│   └── train_clv.py
├── alembic/
├── tests/
│   ├── test_customers.py
│   ├── test_orders.py
│   ├── test_analytics.py
│   └── test_imports.py
├── data/                # local CSV files; decide Git policy
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml       # or requirements.txt
├── README.md
└── docker-compose.yml  # later phase
```

This is a proposed structure aligned to the research's separation of routes, models, schemas, services and configuration.

## 11. Implementation outline and milestone deliverables

### Phase 0 — Requirements and dataset inspection

- Confirm 1,500-cap subset, all nine files and row counts.
- Choose eligible order statuses and monetary definitions.
- Inspect keys, duplicates, missing dates and customer identity.
- Deliverable: data dictionary, relationship diagram, business-rule notes.

### Phase 1 — MySQL schema and ETL

- Create database and Alembic baseline.
- Define normalized SQLAlchemy models and constraints.
- Load parent/reference tables before child tables.
- Import data with reproducible Pandas ETL and log failures.
- Verify row counts, foreign keys, sample joins and sums.
- Deliverable: populated MySQL schema and repeatable import script.

### Phase 2 — Core FastAPI backend (MVP)

- Initialize app, settings, DB session dependency and /docs.
- Build customers/orders listing and detail routes.
- Implement validation, filtering, pagination, error handling.
- Add automated endpoint tests and query-efficiency checks.
- Deliverable: functioning FastAPI + MySQL backend.

### Phase 3 — Cohort and RFM analytics

- Implement first-purchase cohorts and monthly retention.
- Calculate customer purchase history and RFM metrics.
- Expose analytical endpoints and compare SQL/Pandas outputs.
- Deliverable: cohort/RFM JSON endpoints with verified metrics.

### Phase 4 — Predictive CLV

- Validate model prerequisites and fit BG/NBD/Gamma-Gamma where feasible.
- Record convergence/fit results, train/holdout dates and forecast horizon.
- Store predictions for fast API retrieval.
- Deliverable: versioned CLV prediction pipeline or documented data insufficiency.

### Phase 5 — Power BI reporting

- Create star schema with Fact_Order_Items and relevant dimensions.
- Build cohort retention matrix, revenue/RFM/CLV visualizations.
- Test refresh strategy; verify any claimed query folding or incremental refresh.
- Deliverable: Power BI dashboard and metric definitions.

### Phase 6 — Deployment, testing and documentation

- Package app + MySQL with Docker Compose if desired.
- Run Locust load tests; capture actual latency/RPS/error results.
- Add environment setup, schema, API examples, known limitations and screenshots to README.
- Deliverable: reproducible portfolio project and test evidence.

## 12. Backend MVP acceptance checklist

- [ ] Application starts with uvicorn app.main:app --reload.
- [ ] /docs displays documented endpoints.
- [ ] MySQL connection works with configured credentials.
- [ ] Alembic migrations create all required tables.
- [ ] All nine CSVs are imported or exceptions documented.
- [ ] Order, customer, item, payment and review relationships reconcile.
- [ ] Customer history uses customer_unique_id.
- [ ] Customer and order listing APIs return deterministic paginated results.
- [ ] Order detail includes related records without duplicate totals.
- [ ] Invalid input returns 422 and unknown records return 404.
- [ ] A failed database operation does not leave a session open or corrupt the transaction.
- [ ] No database passwords are committed to Git.
- [ ] At least one automated test covers each major route.
- [ ] Cohort/RFM numbers are verified manually for selected customers before expanding the project.

### Example tests

| Test | Input | Expected result |
| --- | --- | --- |
| Pagination | limit=10&offset=0 | 10 or fewer records; accurate total |
| Invalid pagination | limit=0 | 422 |
| Missing order | Unknown order_id | 404 |
| Date validation | start_date > end_date | 422 |
| Customer history | Existing customer_unique_id | All matching eligible orders |
| Order detail | Order with multiple items | No duplicated financial totals |
| Data import | Re-run same ETL | No unintended duplicate records |
| Retention | Known repeat buyer | Correct acquisition month and month offset |

## 13. Risks, caveats and open decisions

| Topic | Risk / decision to resolve |
| --- | --- |
| Reduced dataset | Repeat-customer oversampling biases population-level insights |
| Small sample | CLV models may not converge or generalize |
| Customer IDs | customer_id vs customer_unique_id changes retention calculations |
| Revenue | price, freight_value, and payment_value measure different things |
| Order status | Canceled/undelivered orders affect metrics; define inclusion policy |
| Reviews | Check uniqueness of review_id and join cardinality |
| Geolocation | Reduced ZIP-prefix file may not cover all customers/sellers |
| Model evaluation | Historical holdout must respect chronology; avoid data leakage |
| Power BI | Research presents both API ingestion and direct MySQL/read-replica ingestion; select and document one primary route |
| Deployment | Gunicorn/worker setup and reverse proxy are later-stage choices, not required for local development |
| Security | CORS does not authenticate API users; add authorization if data exposure requires it |

### Recommended build order

Start with: dataset inspection → MySQL schema → CSV ETL → FastAPI customer/order endpoints → tests.
Then add: cohort/RFM analytics → CLV model if feasible → Power BI → Docker/load tests.

This order delivers a demonstrable FastAPI + MySQL project even if the advanced CLV model is not viable on the reduced dataset.

## 14. Research alignment and verified references

### Materials provided in this conversation

- Research report: Strategic Analysis of Integrated Data Analytics and Python Backend Engineering Projects (15 project ideas, top-ranked e-commerce engine).
- Research report: Comprehensive Pre-Project Checklist and Data Architecture for an Enterprise E-Commerce Cohort and Customer Lifetime Value Engine.
- Research report: Enterprise E-Commerce Cohort and Customer Lifetime Value Engine: A Comprehensive Project Blueprint.
- User's ten-category project checklist and the previously generated comprehensive Markdown blueprint.
- The actual README.txt inside the user-provided reduced Olist ZIP (row counts and subset caveats).

### External documentation checked for technical compatibility

- FastAPI — SQL (Relational) Databases: FastAPI supports SQL databases including MySQL and does not require a particular ORM.
- SQLAlchemy 2.0 — Asynchronous I/O: create_async_engine, async_sessionmaker, session lifecycle, expire_on_commit=False, and avoiding implicit I/O.
- Olist Brazilian E-Commerce Dataset: original dataset download and description.

Final note: This document defines what to build. It does not claim that the APIs, database, predictive models, Power BI dashboard, Docker deployment, or performance benchmarks have already been implemented.
