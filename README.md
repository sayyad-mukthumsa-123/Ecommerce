# Olist E-Commerce Analytics and Customer Lifetime Value Engine

## Executive summary

This project turns a linked subset of the Olist Brazilian E-Commerce dataset into a reproducible analytics system. It preserves the raw relational data, prepares and validates MySQL import files, creates post-load analytical extracts, exposes read-only FastAPI endpoints, and presents the results in a nine-page Power BI report.

The main problem is that customer, order, item, payment, review, product, seller, category, and location information is split across different tables and grains. The project joins those sources safely, distinguishes order-level customers from person-level customers, and makes sales, repeat-purchase, cohort, RFM, delivery, and descriptive transaction-value analysis reusable.

Headline takeaway: the current controlled subset contains 1,208 delivered orders and 539 person-level customers, of whom 380 are repeat customers. It is useful for demonstrating an end-to-end analytics architecture, but it is not a representative estimate of the complete Olist marketplace because the selection intentionally prioritizes repeat buyers.

## Project purpose

The project is designed to answer practical e-commerce questions:

1. How many orders, customers, products, sellers, items, payments, and reviews are in the loaded scope?
2. How do item revenue, freight collected, payment totals, and average order value vary over time and category?
3. Which people purchase more than once when identified by `customer_unique_id`?
4. How do acquisition cohorts retain customers over month offsets?
5. Which customers differ in recency, frequency, and monetary value?
6. How long do delivered orders take, and how do delivery metrics vary?
7. Can the prepared transaction extract support future predictive CLV work?

The current system answers the descriptive questions. It produces a CLV transaction extract but does not claim a probabilistic or predictive CLV model.

## Current project status

- Raw-data inventory and relationship validation: complete.
- Prepared CSV generation and quality audit: complete.
- MySQL load and post-load QA: complete for the current batch.
- Step 6 analytical extracts: complete.
- FastAPI read-only API: implemented.
- Power BI report: implemented with nine pages and 99 visual containers.
- Predictive CLV, authentication, production deployment, and a separate web frontend: not implemented.

## Repository structure

```text
E-commerce/
├── backend/             FastAPI app, SQLAlchemy models, API schemas and routers
├── data/
│   ├── raw/             Immutable selected Olist source files
│   ├── prepared/        Controlled MySQL import files
│   ├── quality/         Preparation, import and post-load QA evidence
│   └── analytics/       Step 6 order, RFM, cohort, delivery and CLV extracts
├── Python/              Preparation, post-load pipeline and analysis notebooks
├── SQL/                 Read-only post-load analysis SQL
├── Reports/             Power BI report file
├── tests/               Database-backed backend checks
├── docs/                Detailed folder and process documentation
├── requirements.txt     Pinned Python dependencies
├── .env.example         Safe configuration template
├── .env                 Local secrets and connection settings; never commit
└── .gitignore            Local/generated-file exclusions
```

Detailed inventories are available in [`backend_folder_reference.md`](backend/backend_folder_reference.md), [`data_folder_reference.md`](data/data_folder_reference.md), [`python_folder_reference.md`](Python/python_folder_reference.md), [`reports_folder_reference.md`](Reports/reports_folder_reference.md), [`sql_folder_reference.md`](SQL/sql_folder_reference.md), and [`tests_folder_reference.md`](tests/tests_folder_reference.md). The project runbooks are in [`docs/`](docs/).

## Overall architecture

```text
Olist relational CSV subset
        |
        v
Python preparation and quality checks
        |
        +--> data/prepared/*.csv ----> MySQL ecommerce database
        |                                  |
        |                                  +--> FastAPI read-only API
        |                                  |
        |                                  +--> SQL post-load checks
        |
        +--> data/quality/* audit evidence

MySQL tables --Python/run_post_load_pipeline.py--> data/analytics/*.csv
                                                        |
                                                        +--> FastAPI analytics endpoints
                                                        +--> Power BI Overview.pbix
```

### Data layer

The raw subset contains nine linked CSV datasets. Raw files are treated as immutable inputs. The preparation stage creates controlled copies, preserves source values, adds audit fields, applies approved corrections, and writes exception/quality artifacts. MySQL is the relational serving layer for the API and post-load checks.

### Python layer

[`Python/step3_prepare_data.py`](Python/step3_prepare_data.py) performs preparation and quality handling. [`Python/run_post_load_pipeline.py`](Python/run_post_load_pipeline.py) reads the loaded MySQL tables, validates them, builds order-grain and customer-level extracts, and writes the five current analytics CSVs. The notebooks support profiling and analysis but are not the production load path.

### SQL layer

[`SQL/step6_post_load_analysis.sql`](SQL/step6_post_load_analysis.sql) contains read-only post-load inspection and analysis queries. The Python pipeline is the reproducible writer of the current analytics extracts; SQL is useful for direct database investigation and reconciliation.

### API layer

[`backend/main.py`](backend/main.py) registers health, catalog, customer, order, and analytics routers. [`backend/database.py`](backend/database.py) creates the SQLAlchemy/PyMySQL connection. ORM models represent the nine tables, while Pydantic schemas define the public JSON response contract. The API is read-only and uses parameterized SQL in its route modules.

Implemented route groups include:

- `/health` and `/health/database`;
- `/api/v1/products`, `/sellers`, `/category-translations`, and `/geolocation`;
- `/api/v1/customers` and customer order history;
- `/api/v1/orders` and order details with separate items, payments, and reviews;
- `/api/v1/analytics/summary`, `/monthly-sales`, `/categories`, `/rfm`, `/cohorts`, `/delivery`, and `/transactions`.

### Reporting layer

[`Reports/Overview.pbix`](Reports/Overview.pbix) contains these pages: Executive overview, Sales analysis, Customer analysis, Product and category analysis, Seller analysis, Delivery analysis, RFM analysis, Cohort retention, and CLV transactions. The report uses descriptive measures and transaction extracts; its CLV page is not a predictive forecast page.

## Dataset overview

Source: the Olist Brazilian E-Commerce Public Dataset, reduced to a controlled relational subset. The selection contains complete linked records for selected delivered orders, retains at most 1,500 rows per CSV, and prioritizes repeat buyers across purchase months.

Current scope:

| File | Rows | Grain and important columns |
| --- | ---: | --- |
| `olist_orders_dataset.csv` | 1,208 | One row per order: `order_id`, `customer_id`, `order_status`, purchase/approval/carrier/delivery/estimated timestamps |
| `olist_customers_dataset.csv` | 1,208 | One row per order-linked customer: `customer_id`, `customer_unique_id`, ZIP prefix, city, state |
| `olist_order_items_dataset.csv` | 1,500 | One row per order item: `order_id`, `order_item_id`, `product_id`, `seller_id`, shipping limit, `price`, `freight_value` |
| `olist_order_payments_dataset.csv` | 1,303 | One row per payment sequence: `order_id`, sequence, type, installments, value |
| `olist_order_reviews_dataset.csv` | 1,298 | Review records: source review/order IDs, score, comments, creation and answer timestamps |
| `olist_products_dataset.csv` | 1,096 | Product attributes: ID, category, name/description lengths, photos, weight, dimensions |
| `olist_sellers_dataset.csv` | 494 | Seller ID, ZIP prefix, city, state |
| `product_category_name_translation.csv` | 57 | Portuguese category name and English translation |
| `olist_geolocation_dataset.csv` | 956 | Representative ZIP-prefix latitude, longitude, city, and state |

Purchase timestamps run from 3 October 2016 through 28 August 2018 across 22 observed purchase months. November 2016 is absent. All 1,208 current orders have status `delivered`.

The key person identifier is `customer_unique_id`; `customer_id` identifies the customer record attached to one order. Order-item keys are composite `(order_id, order_item_id)`, payment keys are composite `(order_id, payment_sequential)`, and source `review_id` is not unique. The prepared destination uses a safe review record identifier.

## Data cleaning and preprocessing

### Step 1: raw validation

The raw bundle was inspected before transformation. Headers, counts, relationships, required fields, duplicate behavior, status values, dates, and referential coverage were checked. Raw files remain unchanged under [`data/raw/`](data/raw/).

### Step 2: prepared data

[`Python/step3_prepare_data.py`](Python/step3_prepare_data.py) creates the controlled files under [`data/prepared/`](data/prepared/). It:

- parses date/time fields and preserves source identifiers;
- keeps nullable source fields rather than silently replacing missing values;
- corrects eight invalid lifecycle date sequences in the analysis copy and preserves the original timestamps/audit reason;
- imputes one missing approval timestamp only in `order_approved_at_for_analysis`, preserving the source null;
- imputes 28 rows of optional product-count attributes using prepared-subset medians (`52`, `555`, and `1`) and records flags/methods;
- preserves one zero payment and ten zero freight values as valid observations, with zero imputation/deletion counts;
- preserves optional product/review/comment fields and adds flags for their treatment;
- adds `review_record_id` because 254 rows belong to repeated source `review_id` values;
- writes rejected rows, date corrections, null-handling decisions, manifests, and preparation summaries under [`data/quality/`](data/quality/).

The current controlled MySQL import names include `geolocation_prepared_mysql_normalized.csv` and `reviews_prepared_mysql_binary.csv`.

### Step 3: MySQL load and QA

The nine prepared files were loaded into the `ecommerce` database. QA confirmed expected row counts, zero duplicate composite keys, zero checked orphan relationships, valid review scores, valid payment installments, and valid numeric domains. Identifier columns and audit flags were normalized to readable/text or integer forms after the initial schema correction.

### Step 4: analytical preparation

[`Python/run_post_load_pipeline.py`](Python/run_post_load_pipeline.py) reads the loaded tables and creates an order-grain fact table without joining raw item and payment grains directly. It separately aggregates item revenue, freight, and payment totals, then creates RFM, cohort, delivery, and customer transaction extracts. It does not modify MySQL or claim predictive CLV.

## Methodology and technology stack

| Area | Technology | Use |
| --- | --- | --- |
| Language | Python 3.14 environment | Preparation, validation, analytics, API code |
| Data processing | Pandas, NumPy | CSV preparation, aggregation, quality checks |
| Database | MySQL `ecommerce` | Relational storage and serving layer |
| Database access | SQLAlchemy 2.x, PyMySQL | ORM metadata, sessions, parameterized database access |
| API | FastAPI, Pydantic, Uvicorn | Read-only REST API, validation, OpenAPI docs |
| Analysis | Jupyter, Matplotlib, Seaborn | Profiling, EDA, exploratory visual analysis |
| SQL | MySQL SQL | Post-load QA and direct analysis |
| BI | Microsoft Power BI Desktop | Nine-page semantic/reporting layer |
| Testing | Pytest | Database-backed backend/API checks |
| Configuration | `python-dotenv` | Project-root `.env` loading |

## Key findings and insights

These values are calculated from the current Step 6 outputs and should be interpreted as subset results:

1. **Repeat behavior is unusually strong by design.** There are 539 person-level customers and 380 repeat customers, a repeat-customer rate of approximately **70.50%**. This is a selection effect from the repeat-buyer-prioritized sample, not a marketplace-wide estimate. The Customer and RFM report pages visualize this behavior.
2. **The current order-fact totals reconcile across measures.** Item revenue is **BRL 154,036.12**, freight collected is **BRL 28,306.17**, payment total is **BRL 182,463.62**, and item-plus-freight is **BRL 182,342.29**. The small difference between payment total and item-plus-freight reflects the fact that these are different business measures and must not be substituted.
3. **The average order value based on item-plus-freight is approximately BRL 150.95.** Sales, Executive overview, Product/category, and Seller pages provide the corresponding breakdowns.
4. **Delivery duration averages approximately 12.00 days**, with a minimum of 1.51 and maximum of 70.01 days in the current delivery extract. The Delivery page shows monthly, geographic, distribution, and freight-versus-delivery views.
5. **RFM segments are distributed across four descriptive groups:** regular 192, developing 139, high value 133, and needs attention 75. These are rule-based historical segments, not churn predictions.

The report pages provide charts for these findings, but they should always be read together with the delivered-only and repeat-biased scope caveats.

## Recommendations and next steps

### Business recommendations

- Use `customer_unique_id` for retention and repeat-customer campaigns; do not use order-level `customer_id` as the person identifier.
- Create differentiated engagement for the RFM groups, especially the `high_value` and `needs_attention` segments, while testing campaigns against a properly representative sample.
- Monitor item revenue, freight, and payment total separately because each answers a different financial question.
- Investigate long-delivery orders and freight-heavy categories using the Delivery and Product/category report pages.
- Treat the current report as a diagnostic portfolio/dashboard, not as a population forecast.

### Engineering and analytics next steps

1. Add automated database migrations and a production deployment configuration.
2. Add API authentication/authorization before external exposure.
3. Make analytics extract paths and database settings fully configurable.
4. Add broader automated tests, including API HTTP-level tests, failure-path tests, and reconciliation tests for every extract.
5. Build a chronology-aware train/holdout evaluation before attempting BG/NBD/Gamma-Gamma or another predictive CLV method.
6. Automate future-batch arrival, validation, append, analytics regeneration, and Power BI refresh with approval gates.
7. Add a real web frontend only if a browser application is required; none exists in the current repository.

## Limitations and assumptions

- **Selection bias:** the subset prioritizes repeat buyers and includes only selected linked records. Repeat rates, retention, RFM distributions, and CLV-related values are not representative of all Olist orders.
- **Delivered-only scope:** all current orders are delivered, so this batch cannot compare canceled, shipped, unavailable, or other order statuses.
- **Small time/sample scope:** 1,208 orders and 539 people may be insufficient for reliable predictive CLV or churn modeling.
- **No predictive CLV:** `clv_transactions_step6.csv` is a descriptive transaction extract. It is not a forecast, profit model, or churn probability.
- **Review IDs:** source `review_id` values repeat; review ID alone is not a safe primary key.
- **Geolocation:** one representative original geolocation row is retained per referenced ZIP prefix rather than the full original multiplicity.
- **Date corrections:** eight lifecycle date corrections and one approval imputation are applied only to prepared analysis fields; source values are retained for audit.
- **Valid zeroes:** one zero payment and ten zero freight values are retained as observed values, not imputed.
- **Metric definitions:** payment totals, item revenue, freight, and item-plus-freight are distinct measures; financial interpretation must specify which one is being used.
- **Local architecture:** the API assumes a reachable local MySQL database and local analytics files. It is not yet hardened for public production traffic.
- **No frontend:** there is no React, Next.js, Vite, or other web frontend folder. Power BI is the current reporting interface.

## Environment setup

### Prerequisites

Install:

- Git;
- Python 3.14 or the compatible version used by the project virtual environment;
- MySQL Server and MySQL Workbench (or an equivalent MySQL client);
- Power BI Desktop if the report must be opened or refreshed.

### Clone or obtain the project

If the project is hosted in Git:

```powershell
git clone <repository-url> E-commerce
cd E-commerce
```

If it is already downloaded, open PowerShell in the project root:

```powershell
cd C:\Users\mukth\OneDrive\Desktop\E-commerce
```

### Create the virtual environment

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use the project interpreter directly:

```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Configure environment variables

Copy [`.env.example`](.env.example) to `.env`, or run:

```powershell
Copy-Item .env.example .env
```

Set a real MySQL connection string in `.env`:

```text
DATABASE_URL=mysql+pymysql://<user>:<password>@localhost:3306/ecommerce
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:8000
```

Never commit `.env` or place passwords in source code. The current application reads `DATABASE_URL` and `ALLOWED_ORIGINS`; `APP_NAME`, `APP_VERSION`, and `DEBUG` are not required by the current `main.py` implementation.

## Running the components

### Prepare data

From the project root, after the raw files are present:

```powershell
& .\.venv\Scripts\python.exe Python\step3_prepare_data.py
```

Review [`data/prepared/`](data/prepared/) and [`data/quality/`](data/quality/) before importing into MySQL. Do not import raw files directly.

### Load and validate MySQL

Use the approved prepared files and the documented MySQL import procedure. After loading all nine tables, review [`data/quality/load_qa_results.md`](data/quality/load_qa_results.md). The database must contain `customers`, `orders`, `order_items`, `payments`, `reviews`, `products`, `sellers`, `category_translation`, and `geolocation`.

### Generate analytics extracts

```powershell
& .\.venv\Scripts\python.exe Python\run_post_load_pipeline.py --batch-id STEP3-20261121-001
```

The command reads MySQL and updates [`data/analytics/`](data/analytics/) plus post-load quality artifacts. It does not modify MySQL. The full future-batch process is in [`docs/future_batch_data_runbook.md`](docs/future_batch_data_runbook.md).

### Run the backend

```powershell
& .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Open:

- `http://127.0.0.1:8000/docs` for Swagger UI;
- `http://127.0.0.1:8000/redoc` for ReDoc;
- `http://127.0.0.1:8000/health` for application/database health.

The backend reference is [`docs/step_7_fastapi_backend.md`](docs/step_7_fastapi_backend.md).

### Run backend tests

The tests require the configured MySQL database and current analytics extracts:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/test_backend_basic.py -q
```

### Run SQL analysis

Open [`SQL/step6_post_load_analysis.sql`](SQL/step6_post_load_analysis.sql) in MySQL Workbench and execute its read-only queries against the `ecommerce` database. The Python pipeline remains the canonical writer of the current Step 6 CSV outputs.

### Run notebooks

Start Jupyter from the project root:

```powershell
& .\.venv\Scripts\python.exe -m jupyter lab
```

Relevant notebooks are [`Python/pre-analysis.ipynb`](Python/pre-analysis.ipynb), [`Python/Pre-processing.ipynb`](Python/Pre-processing.ipynb), and [`Python/step6_post_load_analysis.ipynb`](Python/step6_post_load_analysis.ipynb). Run them only after reviewing their input paths and ensuring that outputs will not overwrite controlled artifacts unintentionally.

### Open the report

There is no separate frontend server. Open the Power BI report directly:

```powershell
Start-Process Reports\Overview.pbix
```

In Power BI Desktop, confirm the source connection and select **Home → Refresh** after the analytics pipeline succeeds. Do not refresh from a failed pipeline run.

## Reproducibility and documentation conventions

This project keeps raw data, prepared data, QA evidence, code, outputs, and documentation in separate areas. The project-level README follows common data-project guidance to document provenance, data relationships, methodology, dependencies, reproducible setup, file inventory, limitations, and reuse conditions. Good README practice also recommends describing how files relate, what transformations occurred, which software versions were used, and how another user can reproduce the result.

The design was informed by:

- [UCSB Data README guidance](https://rcd.ucsb.edu/sites/default/files/2023-03/dls-n03-2021-README_white.pdf)
- [LMU Open Science Center data-management guidance](https://www.osc.lmu.de/training/research-cycle-handbook/02-collect-and-manage.html)
- [University of Melbourne data documentation guidance](https://library.unimelb.edu.au/Digital-Scholarship/data/knowledge-bank/documenting-and-describing-data)
- [World Bank reproducibility FAQs](https://worldbank.github.io/wb-reproducible-research-repository/reproducibility_FAQs.html)

These references support documenting provenance, data dictionaries, file relationships, processing methods, dependency versions, environment setup, and reproducible execution order.
