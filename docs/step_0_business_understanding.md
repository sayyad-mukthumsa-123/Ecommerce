# Step 0 — Business Understanding, Scope, and Project Setup

**Project:** Enterprise E-Commerce Cohort and Customer Lifetime Value Engine  
**Completed:** 19 November 2026  
**Status:** Step 0 documented; two technical setup gaps remain before backend implementation.

## 1. Business objective

Build a reproducible e-commerce analytics solution that moves from the approved Olist relational data to:

- validated MySQL tables;
- post-load exploratory analysis and customer/order metrics;
- a FastAPI backend for customer and order access;
- Power BI semantic models and reports; and
- a controlled future-data process that loads a new approved batch into MySQL and refreshes Power BI.

The project is an analytics and engineering portfolio system. It is not a shopping cart, checkout, payment-processing, or real-time marketplace application.

## 2. Questions the project should answer

1. How many orders, customers, repeat customers, products, sellers, and reviews are in the loaded data?
2. How do orders and monetary measures change over purchase month, category, seller, and geography?
3. Which `customer_unique_id` values return, and how does retention vary by acquisition cohort?
4. Which customers or segments differ by recency, frequency, and monetary value?
5. How do payment type, review score, freight, and delivery timing relate to order behavior?
6. Can a revenue-based CLV estimate be justified after descriptive cohort/RFM analysis and chronological validation?

## 3. Scope and data facts

The approved source is the final bundle under `../data/raw/olist_trimmed_1500_relational/`:

- 1,208 orders and 1,208 order-linked customers;
- 1,500 order items;
- 1,303 payment rows;
- 1,298 review rows;
- 1,096 products;
- 494 sellers;
- 57 category translations; and
- 956 representative geolocation rows.

The subset contains 539 distinct `customer_unique_id` values and 380 repeat customers. All orders are delivered, and purchase timestamps span 2016-10-03 through 2018-08-28.

This is a deliberately selected, repeat-customer-prioritized subset. It must not be presented as representative of the full Olist population. Geolocation contains one original record per referenced ZIP prefix, not every original coordinate observation.

## 4. Agreed stack

| Area | Selected technology | Use |
| --- | --- | --- |
| Programming | Python | Project scripts, API, and analytics |
| Data preparation | Pandas, NumPy | CSV profiling, preprocessing, metrics, and extracts |
| EDA | Matplotlib, Seaborn | Quality checks and analytical visualizations |
| Database | MySQL | Persistent storage and governed reporting source |
| Database access | SQLAlchemy + PyMySQL | FastAPI and post-load analytical access to MySQL |
| API validation | Pydantic | Settings, request models, and response models |
| API | FastAPI | Customer, order, and analytical endpoints |
| Reporting | Power BI | Semantic model, DAX measures, reports, and refresh |

Initial CSV loading will use MySQL Workbench's Table Data Import Wizard into destination tables. SQLAlchemy/PyMySQL are for application and analytical access after the tables have been loaded; they are not the initial CSV import mechanism.

## 5. Confirmed project rules

- Preserve the raw files unchanged and keep each future delivery as a versioned batch.
- Use `customer_id` for order linkage and `customer_unique_id` for person-level analysis.
- Keep order items and payments at separate grains; aggregate them independently before combining order-level measures.
- Treat `review_id` as non-unique and preserve it as a source field rather than assuming it is a table primary key.
- Preserve source nulls; do not silently synthesize or replace values.
- Use separate, explicitly named measures for item revenue, freight collected, and order payment totals.
- Use delivered orders for realized-sales, cohort, retention, and CLV analysis in this subset.
- Label descriptive metrics separately from any predictive CLV output.

## 6. Setup readiness check

| Check | Observed status | Action |
| --- | --- | --- |
| Project root and `docs/` folder | Ready | Continue using the current workspace. |
| Raw data bundle | Ready | Use the validated files and validation report. |
| Python virtual environment | Present as `.venv/` | Confirm its interpreter before installing missing project dependencies. |
| `.env` | Contains `DATABASE_URL` key | Keep the value local; never copy it into documentation or source control. |
| `.gitignore` | Excludes `.env`, virtual environments, and caches | Keep this protection in place. |
| `requirements.txt` | Updated with pinned FastAPI, SQLAlchemy, PyMySQL, and Pydantic dependencies | Keep the pins synchronized with the selected environment. |
| `main.py` and `database.py` | Corrected and verified | SQLAlchemy resolves the configured URL to the MySQL/PyMySQL dialect, and the live `SELECT 1` health check passed. |

## 7. Step 0 exit criteria

- [x] Business objective and non-goals are documented.
- [x] Business questions and expected report consumers are documented.
- [x] Final raw-data scope and limitations are recorded.
- [x] Technology stack and initial MySQL import method are agreed.
- [x] Data identity, grain, null, review-ID, and monetary-measure rules are documented.
- [x] Raw data validation evidence is available in `../data/raw/olist_trimmed_1500_relational/validation_report.json`.
- [x] Secret-handling rule is confirmed; `.env` values are not copied into this file.
- [x] Runtime dependencies are pinned for the agreed stack.
- [x] FastAPI and SQLAlchemy/PyMySQL connection setup is corrected and verified with a live database health check.

Proceed to Step 1: get, register, and freeze the raw data.
