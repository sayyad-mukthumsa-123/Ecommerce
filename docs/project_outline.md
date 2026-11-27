# Enterprise E-Commerce Cohort and Customer Lifetime Value Engine

**FastAPI + MySQL Project Requirements and Implementation Outline**

- Document type: Project Requirements Document (PRD) + Software Requirements Specification (SRS) + Implementation Outline
- Prepared: 19 November 2026
- Status: Current implementation and planning reference; the raw bundle, MySQL load, FastAPI API, Step 6 extracts, and nine-page Power BI report are implemented. Predictive CLV and production deployment remain future work.
- Project focus: Python backend engineering, MySQL data management, e-commerce analytics, and eventual Power BI reporting
- Source distinction: Sections describing the current batch, backend, analytics extracts, and Power BI pages are verified against the workspace. Advanced modeling, deployment, and future-batch requirements remain planning guidance and must not be read as implemented unless explicitly marked.

## Current implementation snapshot — 27 November 2026

- The current raw subset contains 1,208 orders, 539 person-level customers, and 380 repeat customers; all current orders are delivered.
- The nine prepared MySQL inputs are loaded and reconciled. Step 6 produces order-fact, RFM, cohort, delivery, and descriptive CLV transaction extracts under [`data/analytics/`](../data/analytics/).
- The implemented FastAPI application is documented in [`step_7_fastapi_backend.md`](./step_7_fastapi_backend.md). It includes health, catalog, customer, order, and analytics routes.
- [`Reports/Overview.pbix`](../Reports/Overview.pbix) contains nine report pages and 99 visual containers. The current report is descriptive; it does not claim a predictive CLV model.
- The repeatable future-batch and report-refresh process is documented in [`future_batch_data_runbook.md`](./future_batch_data_runbook.md).
- The remaining roadmap is predictive CLV validation, production hardening, authentication, deployment, and future-batch automation beyond the current local process.

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

Current working data: the final files in `data/raw/olist_trimmed_1500_relational/`. The subset has at most 1,500 rows per CSV, not 1,500 customers or orders in every table. `README_RELATIONSHIPS.md` and `validation_report.json` document the selection, joins, row counts, and validation results. The source records and optional missing values are preserved; geolocation is reduced to one original record per referenced ZIP prefix.

| CSV file | Rows in current subset | Purpose |
| --- | --- | --- |
| olist_orders_dataset.csv | 1,208 | Delivered orders, status, lifecycle timestamps |
| olist_customers_dataset.csv | 1,208 | Order-linked customer records and customer_unique_id |
| olist_order_items_dataset.csv | 1,500 | Line items, product, seller, price, freight |
| olist_order_payments_dataset.csv | 1,303 | Payment types, installments and values |
| olist_order_reviews_dataset.csv | 1,298 | Review scores and comments |
| olist_products_dataset.csv | 1,096 | Product attributes |
| olist_sellers_dataset.csv | 494 | Seller attributes |
| product_category_name_translation.csv | 57 | Portuguese-to-English category names |
| olist_geolocation_dataset.csv | 956 | One original coordinate record per referenced ZIP prefix |

The subset contains 539 distinct `customer_unique_id` values, including 380 repeat customers. Purchase timestamps range from 2016-10-03 through 2018-08-28. Every order in this final subset has status `delivered`, and every order has at least one item, payment, and review row.

### Critical data rules

- customer_id identifies an order-linked customer record; customer_unique_id identifies a repeat customer across orders. Do not calculate repeat customers using customer_id alone.
- Order items are not uniquely identified by order_item_id alone; use the composite (order_id, order_item_id).
- Payments may contain multiple records per order; preserve (order_id, payment_sequential) as a candidate composite key after validation.
- Reviews require a surrogate/composite key if `review_id` is used as an identifier: `review_id` is not unique in this subset, so do not make it the sole primary key.
- Geolocation ZIP prefixes can occur repeatedly in the original dataset; the current reduced file is unique by prefix and contains a matching record for every referenced customer and seller prefix. The retained record is a representative lookup, not the full original geolocation observation set.
- Because this subset deliberately prioritizes repeat purchasers, retention percentages and CLV behavior will not represent the original Olist population. Treat them as educational subset results, not market estimates.
- With 1,208 orders and 380 repeat customers, probabilistic CLV models may still have too little time depth for reliable fitting; report convergence and holdout limitations honestly.

### Final dataset validation evidence

- [x] Confirm final filenames, headers, row counts, and key fields.
- [x] Check nulls and duplicates; optional source missing values remain preserved.
- [x] Verify primary and composite keys. Orders, customers, products, sellers, item keys, payment keys, geolocation prefixes, and category translations pass uniqueness checks.
- [x] Check order/customer/item/payment/review relationships and referenced products/sellers.
- [x] Check timestamps and status values; all 1,208 orders are delivered.
- [x] Verify 539 distinct `customer_unique_id` values and 380 repeat customers.
- [x] Preserve raw input files unchanged.

See `data/raw/olist_trimmed_1500_relational/validation_report.json` for the machine-readable report. Its validation checks pass for all listed relationships, and it records the intentional caveats for review IDs and geolocation multiplicity.

## 3. End-to-end execution runbook: raw files to Power BI reports

This is the ordered implementation process for the project. Complete each step's exit criteria before moving to the next step. The final raw files are inputs; generated staging files, database tables, API outputs, analytical extracts, and Power BI reports are derived artifacts and must be reproducible.

### Step 0 — Business understanding, scope, and project setup

1. Define the business questions: sales/order performance, customer repeat behavior, cohorts, RFM, reviews, delivery performance, and optional revenue-based CLV.
2. Define the audience, reporting grain, KPI definitions, success criteria, refresh expectation, and known subset-bias limitation before touching the data.
3. Confirm the project root and keep the approved inputs under `data/raw/olist_trimmed_1500_relational/`.
4. Create or confirm the Python virtual environment and install the pinned dependencies from `requirements.txt`: Python, NumPy, Pandas, Matplotlib, Seaborn, SQLAlchemy, PyMySQL, Pydantic, and FastAPI.
5. Configure `.env` for local MySQL credentials, database name, API settings, and Power BI connection settings. Never commit secrets.
6. Create a working branch and record the dataset version, validation-report timestamp, and reporting/model version.

See [Step 0 — Business Understanding, Scope, and Project Setup](./step_0_business_understanding.md) for the completed scope decision, data facts, stack agreement, readiness check, and remaining setup gaps.

Exit criteria: business questions and metrics are documented, the environment starts, secrets are local-only, and the raw folder is treated as read-only source data.

### Step 1 — Get, register, and freeze the raw data

1. Obtain the approved Olist CSV bundle and place the nine CSV files, `README_RELATIONSHIPS.md`, and `validation_report.json` under `data/raw/olist_trimmed_1500_relational/`.
2. Record the acquisition date, source/version, file names, encodings, headers, row counts, and source checksums in the ETL run log.
3. Read the relationship README and validation JSON before writing transformations.
4. Preserve the raw bundle as immutable input. Do not rename source columns or overwrite raw files; apply naming changes only in staging or warehouse tables.
5. For future deliveries, store each raw-data version separately and assign a batch ID so a failed load can be traced and rolled back.

Expected final counts: 1,208 orders, 1,208 customers, 1,500 order items, 1,303 payments, 1,298 reviews, 1,096 products, 494 sellers, 57 category translations, and 956 geolocation rows.

Step 1 completed for the current batch: all expected files are present, no unexpected files were found, CSV row counts match `validation_report.json`, and raw-file SHA-256 checksums are recorded in [raw_data_inventory.json](raw_data_inventory.json). No raw files were overwritten.

Exit criteria: the inventory matches the validation report and every import run can identify the exact source files used.

### Step 2 — Data understanding and initial profiling

1. Use Pandas to inspect file shapes, columns, data types, missingness, distinct values, duplicates, date ranges, order statuses, and relationship coverage.
2. Use Matplotlib and Seaborn for initial profiling visuals: distributions, time coverage, order status counts, review scores, price/freight values, and missing-value patterns.
3. Read `README_RELATIONSHIPS.md` and `validation_report.json` and compare their claims with the observed files.
4. Identify the grain of every table and document primary keys, composite keys, foreign keys, and known caveats such as non-unique `review_id`.
5. Record that all final orders are `delivered`, purchase dates span 2016-10-03 to 2018-08-28, and the subset contains 539 unique people with 380 repeat customers.
6. Decide which fields are retained, renamed in the destination table, excluded from reporting, or preserved as nullable source attributes.

Exit criteria: the analyst understands the data grain and limitations, the profiling findings are recorded, and the data dictionary/relationship map is ready for preprocessing.

### Step 3 — Pre-load preprocessing and quality checks

1. Work from immutable copies of the nine raw CSVs. Confirm the Step 2 inventory before transforming: 1,208 orders, 1,208 customers, 1,500 items, 1,303 payments, 1,298 reviews, 1,096 products, 494 sellers, 57 translations, and 956 geolocation rows.
2. Use Pandas and NumPy to normalize data types. Parse all order, shipping, and review timestamps as datetimes; preserve all business identifiers and ZIP prefixes as strings, including customer, seller, and geolocation ZIP prefixes.
3. Validate the observed time scope and status values: purchase dates run from 2016-10-03 through 2018-08-28, the subset contains 22 observed purchase months, and all 1,208 current orders are `delivered`. Record that the current subset cannot support status-to-status comparisons because no other statuses are present.
4. Validate primary keys, composite keys, foreign-key coverage, required columns, and duplicate behavior before import. Enforce `order_id`, `customer_id`, `product_id`, and `seller_id` uniqueness; enforce `(order_id, order_item_id)` and `(order_id, payment_sequential)` as composite keys; and confirm every order has at least one item, payment, and review.
5. Treat `review_id` as a source attribute, not a primary key: the preprocessing notebook found 254 rows belonging to repeated `review_id` values. Add a destination surrogate key or another validated safe key while preserving the original `review_id` unchanged.
6. Apply the approved null-handling decisions consistently. Preserve the source `order_approved_at` null, but impute the approved value `2017-02-19 01:28:47` only in the derived `order_approved_at_for_analysis` column for order `d69e5d356402adc8cf17e08b5033acfb`; retain an imputation flag and method. Preserve raw product attributes and optional comments unchanged, but impute the 28 missing prepared product count values using prepared-subset medians (`product_name_lenght=52`, `product_description_lenght=555`, `product_photos_qty=1`) and retain flags/methods. Keep product category nulls as nullable source values with flags. Treat the one zero payment and ten zero freight values as valid observed zeroes: retain them and do not impute or delete them.
7. Standardize column names only in prepared copies/data frames and create a raw-to-destination data dictionary. Correct source spelling only in the destination mapping when appropriate, while retaining the original source column names in the raw-to-prepared audit.
8. Keep orders, order items, payments, and reviews at their original grains. Keep order items and payments as separate data frames and aggregate them independently before creating any order-grain fact table; do not join raw items and payments directly.
9. Re-run relationship checks explicitly, including the order-to-customer check that was commented out in the notebook. Confirm all item order/product/seller references, payment and review order references, product-category translations, and customer/seller geolocation references.
10. Validate numeric fields before import: review scores must be 1–5; prices, freight, payments, installments, and product dimensions must have valid domains; retain the one zero payment and ten zero freight values as valid observed values with zero imputation/deletion counts; and flag extreme right-tail values rather than deleting them automatically.
11. Record the observed numeric baseline for reconciliation: item price has median BRL 69.90 and maximum BRL 4,399.87; freight has median BRL 16.11 and maximum BRL 196.94; payment value has median BRL 89.75, zero minimum, and maximum BRL 4,513.32; installments range from 1 to 21.
12. Define `customer_id` for order-level linkage and `customer_unique_id` for person-level cohorts, retention, RFM, and CLV. The current baseline is 539 unique people and 380 repeat customers; use this as a reconciliation check, not as a population estimate.
13. Define separate measures for `item_revenue`, `freight_collected`, and `order_payment_total`. Keep all amounts labeled as BRL, document whether each measure is item-, freight-, or payment-based, and do not use one as a substitute for another.
14. Define the current eligible-order rule as delivered orders for realized sales and retention, while retaining `order_status` for operational/API filtering. Document that the current data was selected from delivered orders and is not a representative full-population sample.
15. Quarantine invalid rows and exceptions with a reason; never silently drop them. Produce exception outputs for invalid dates, key violations, orphan references, invalid review scores, invalid numeric domains, and any row-count mismatch.
16. State the sampling caveat on every report: this is a repeat-customer-prioritized subset, so the high repeat-customer share, cohort retention, review distribution, and any CLV result are educational subset results rather than market estimates.

Exit criteria: prepared copies pass type, key, relationship, null, and domain checks; the review-key strategy is documented; exception rows are accounted for; metric definitions are approved; and the same names/definitions are used by SQL, API responses, and Power BI measures.

### Step 4 — Prepare MySQL tables for direct table-data import

1. From this step onward, use only the verified files in `data/prepared/` as operational inputs. Use `data/raw/olist_trimmed_1500_relational/` only as immutable audit/reference data; never import raw CSVs directly. Apply the approved Step 3 date-correction policy before MySQL import. For the seven orders with carrier dates before approval, set the prepared `order_delivered_carrier_date` equal to the approved analysis timeline; for the one order with customer delivery before carrier handoff, set the prepared delivery date equal to the carrier date. Preserve the original raw timestamps in audit columns, add correction flags/reasons, and do not alter raw CSVs. Import both the nullable source `order_approved_at` and derived `order_approved_at_for_analysis`; the latter contains one documented imputation and has no remaining nulls.
2. Register the generated `data/quality/date_corrections.csv`, `step3_preparation_summary.csv`, and import manifest as Step 3 audit artifacts. Confirm that the nine files in `data/prepared/` exist, their row counts match the manifest, and their schemas are approved before import. Treat notebook file-save problems as environment issues, not data-quality findings; the prepared files and audit artifacts are the controlled inputs/evidence for import.
3. Use the already-created MySQL database `ecommerce`; do not recreate or drop the database. Confirm that the Workbench connection points to `ecommerce` before creating tables. No persistent SQL script is required for this step.
4. Create or verify the nine destination tables in `ecommerce` before importing any CSV. The current implementation stores identifiers and ZIP prefixes as text-compatible values, numeric flags as integer values, counts/sequences/scores as integers, measurements and monetary values as doubles, and timestamps as datetimes. Keep all nullable source and optional fields nullable. Verify the actual live schema before changing this mapping.
5. Use the MySQL Workbench Table Data Import Wizard only after the tables exist. Select the nine prepared inputs, including `geolocation_prepared_mysql_normalized.csv` and `reviews_prepared_mysql_binary.csv`, and record each file path, row count, columns, encoding, delimiter, null marker, and validation status before loading. Missing values in every prepared CSV are represented by the MySQL text-import marker `\\N`; do not replace them with empty strings, the literal word `NULL`, or numeric zero. Configure the import to interpret `\\N` as SQL `NULL` and keep the corresponding destination columns nullable.
6. Import parent/reference tables first: category translation, geolocation, customers, sellers, and products. Then import orders, order items, payments, and reviews. The Step 4 table definitions intentionally do not add foreign keys because the allowed direct-import types do not support indexed `TEXT` keys reliably; validate all relationships in Step 5 after loading.
7. Keep source identifiers and source nulls unchanged. Store the null-handling decision log with the batch, keep `order_approved_at_for_analysis` separate from source `order_approved_at`, retain zero payment/freight values unchanged, and use `review_record_id` as the review row identifier because source `review_id` is repeated. The current controlled import files are `geolocation_prepared_mysql_normalized.csv` and `reviews_prepared_mysql_binary.csv`; do not substitute older script-default names without reviewing the mapping.
7. Keep source identifiers and source nulls unchanged. Store the null-handling decision log with the batch, and keep `order_approved_at_for_analysis` explicitly separate from source `order_approved_at`. Add audit fields such as `batch_id`, `source_file`, `preprocessing_status`, and `validation_exception` rather than overwriting source data.
8. Do not use a query-driven ETL or an ORM-driven initial load. SQLAlchemy/PyMySQL will be used later by FastAPI and analytical scripts to connect to the loaded MySQL database.
9. Capture screenshots or export the Workbench import settings and record destination table names, column mappings, encoding, delimiter, prepared-file paths, exception counts, and import batch ID.

Exit criteria: the nine tables exist in the existing `ecommerce` database, their column counts and allowed MySQL types match the prepared inputs, all eight timestamp corrections and the one derived approval imputation remain reproducible from audit files, import settings are ready to be recorded, and no raw or prepared file has been overwritten.

### Step 5 — Import data into MySQL and perform load QA

1. Import only the verified files from `data/prepared/`, using the recorded delimiter, encoding, column mapping, destination table, and preprocessing batch ID. Import the corrected prepared dates, not the unchanged raw date fields.
2. Import in dependency order: customers/products/sellers/category translations/geolocation, then orders, order items, payments, and reviews.
3. Preserve source identifiers and source nulls; load `order_approved_at_for_analysis` as the controlled derived analysis field and verify one approval imputation plus 28 documented product-count imputations. Do not synthesize any other business values during import. Keep order items, payments, and reviews at their source grains and do not import a pre-joined item/payment dataset.
4. After each import, compare MySQL row counts with the prepared file. Reconcile the eight corrected orders to `date_corrections.csv`, verify source approval null count 1 versus analysis approval imputation count 1 and remaining analysis null count 0, and do not report a count mismatch or missing correction audit as a successful load.
5. Run read-only SQL validation queries for primary keys, composite keys, orphan foreign keys, delivered-only status coverage, date ranges, null patterns, numeric domains, category/geolocation coverage, and expected order coverage.
6. Confirm that the Step 3 zero-domain checks remain valid: no negative item or payment amounts, no invalid installment counts, no invalid review scores, one retained zero payment value, and ten retained zero freight values. Verify the 28 product-count imputations and zero payment/freight imputation or deletion counts; investigate context without changing valid zeroes.
7. Verify that every loaded order has item, payment, and review relationships and that item and payment tables remain at their original grains.
8. Reconcile the loaded totals to the Step 3 baseline: 1,208 orders, 1,208 customers, 1,500 items, 1,303 payments, 1,298 reviews, 1,096 products, 494 sellers, 57 translations, and 956 geolocation rows, adjusted only for explicitly approved quarantines.
9. Record source counts, loaded counts, rejected counts, exception counts, duration, batch ID, Workbench settings, and validation results in the load log.
10. If the import fails, preserve the failed-batch evidence, correct only the prepared copy or destination mapping, and rerun as a new controlled attempt.
11. Load QA completed for the current batch: category translation 57, customers 1,208, geolocation 956, sellers 494, products 1,096, orders 1,208, order items 1,500, payments 1,303, and reviews 1,298. The source approval null count is 1, analysis approval null count is 0, approval imputation count is 1, product-attribute imputation count is 28, zero-payment count is 1, and zero-freight count is 10. Duplicate composite keys, invalid numeric domains, invalid review scores, invalid order-date sequences, and all checked orphan relationships returned zero. `local_infile` was enabled only for the controlled load and turned off afterward.

Exit criteria: all prepared rows are loaded, counts reconcile, post-load SQL checks pass, all eight date corrections and the one approval imputation are traceable, valid zero values are retained without imputation/deletion, and the load log contains the evidence. This exit criterion is met for the current import batch.

### Step 6 — Post-load preprocessing, EDA, and analytical modeling

1. Query the loaded MySQL tables through SQLAlchemy and create validated Pandas analytical DataFrames. Use `order_approved_at_for_analysis` for lifecycle metrics, retain the source nullable approval field, and retain the eight date-correction flags, one approval imputation, 28 product-count imputation flags, and source-date audit columns.
2. Create an order-grain fact dataset with one row per order and separately verified item, freight, and payment totals. Do not join raw items and payments before aggregation.
3. Create customer-level metrics using `customer_unique_id` for person-level analysis. Reconcile 539 unique people and 380 repeat customers before building cohorts or RFM.
4. Build cohorts from each person's first eligible delivered purchase month and calculate monthly retained customers and retention rates. Document the 22 observed purchase months and the absence of November 2016.
5. Build RFM segments using documented units and a fixed historical observation cutoff. Do not use the current date as the cutoff.
6. Calculate delivery-duration metrics from the corrected prepared dates and the analysis approval timeline, report eight boundary corrections and one approval imputation, and retain separate source-versus-prepared audit comparisons. Do not silently mix raw inconsistent intervals with corrected analytical intervals.
7. Use Matplotlib and Seaborn for post-load EDA: distributions, monthly order trends, cohort-retention heatmaps, RFM segments, price/freight behavior, review scores, delivery timing, zero-value amounts, and data-quality exceptions.
8. Preserve the one zero payment value and ten zero freight values as source observations, investigate their order context, document that neither was imputed or deleted, and state whether each analytical measure includes them.
9. Prepare CLV transactions at customer/order grain. Use descriptive RFM and cohort analysis as the baseline; do not claim a probabilistic CLV model unless convergence, assumptions, and chronological holdout evaluation are documented.
10. Store reusable analytical outputs as MySQL views/tables or controlled extracts for Power BI and API consumption.
11. Version analytical outputs with observation cutoff, forecast horizon, model version, preprocessing batch ID, exception count, and generation timestamp.
12. Reconcile a sample of customers and orders across prepared CSV, MySQL, EDA outputs, and analytical results. Consult raw CSVs only to verify provenance or investigate an exception; do not use raw values as analytical inputs.

Exit criteria: post-load quality is verified, timestamp exceptions and zero-value amounts are documented, EDA findings are recorded, analytical outputs are reproducible, and metric definitions are consistent.

### Step 7 — Build and verify the FastAPI backend

1. Configure FastAPI, the SQLAlchemy engine/session factory using PyMySQL, Pydantic response models, request lifecycle, and health endpoints after the MySQL load QA passes. This is implemented in `backend/` and documented in [`step_7_fastapi_backend.md`](./step_7_fastapi_backend.md).
2. Implement paginated customer and order listing endpoints with deterministic ordering and explicit delivered-order/status filtering.
3. Implement customer lookup by `customer_id` and `customer_unique_id`; ensure person-level history uses `customer_unique_id` and reconciles to 539 unique people and 380 repeat customers.
4. Implement order details with separately loaded items, payments, and reviews. Do not return duplicated item/payment totals caused by multi-grain joins.
5. Implement Product, Seller, CategoryTranslation, and Geolocation catalog schemas and paginated lookup endpoints using direct parameterized SQL in the API layer.
6. Implement status/date filters and standard 404, 422, and 500 error behavior. Document how the eight lifecycle-exception orders are represented.
7. Expose summary, monthly-sales, category, cohort, RFM, delivery, and descriptive transaction endpoints after the analytical outputs and separate financial totals are reconciled. Predictive CLV is not exposed.
8. Add OpenAPI descriptions and tests for pagination, missing IDs, date validation, customer history, catalog lookups, multi-item orders, duplicate review IDs, source-versus-analysis approval timestamps, valid zero payment/freight visibility, exception-flag visibility, and database read failures.

Exit criteria: met for the current local MVP. The service starts locally, `/docs` renders, the focused integration checks pass, API totals reconcile to MySQL/analytics, and current exception/status behavior is documented in [`step_7_fastapi_backend.md`](./step_7_fastapi_backend.md).

### Step 8 — Prepare the Power BI semantic model

1. Choose one governed source: direct read-only MySQL views for development/reporting or a controlled Pandas-generated extract. Do not connect Power BI directly to the raw folder.
2. Build a star schema with a fact table at the chosen order or order-item grain and dimensions for date, customer, product, seller, geography, and category.
3. Keep payments and order items at separate grains unless they have been safely aggregated before joining. Preserve `item_revenue`, `freight_collected`, and `order_payment_total` as separate measures.
4. Add a calendar table and mark it as the date table. Include the observed purchase period and the missing November 2016 month without fabricating rows.
5. Define Power Query transformations for string identifiers/ZIP prefixes, nullable source fields, `order_approved_at_for_analysis`, category translation, null-handling flags, exception flags, and refresh parameters. Keep complex cleaning in Pandas/SQL so Power BI remains a reporting layer.
6. Define DAX measures for orders, customers, repeat customers, item revenue, freight, payments, average order value, cohorts, retention, RFM, and CLV. Clearly label descriptive measures and revenue-based CLV.
7. Add a data-quality page showing refresh date, source row counts, rejected rows, eight lifecycle exceptions, one approval imputation with zero remaining analysis nulls, one retained zero payment, ten retained zero freight values, zero imputation/deletion counts for those zeroes, and validation status.

Exit criteria: Power BI totals reconcile to the MySQL analytical layer and refresh succeeds without manual file edits.

### Step 9 — Build the Power BI report pages

1. Create an executive overview with orders, customers, repeat-customer rate, separately defined item revenue/freight/payment measures, average order value, and date filters.
2. Create a cohort-retention page with acquisition cohorts, month offsets, retained customers, and retention percentages. Label the results as subset-specific because repeat customers were prioritized.
3. Create a customer/RFM page with segment counts, recency/frequency/monetary distributions, and drill-through to customer history using `customer_unique_id`.
4. Create an order/product page with category, seller, freight, price, payment type, review score, delivery timing based on the analysis approval timestamp, zero-value measures, and lifecycle-exception counts.
5. Create a CLV page only when model outputs pass the documented validation gates; label forecasts as revenue-based CLV, not profit, and show model version, cutoff, horizon, and limitations.
6. Add tooltips, definitions, filter behavior, data-quality status, and a limitations panel describing delivered-only scope, repeat-customer prioritization, lifecycle exceptions, and representative geolocation.

Exit criteria: each visual has a defined measure, slicers behave consistently, and the report tells users which metrics are descriptive versus predictive.

### Step 10 — Reconcile, publish, refresh, and hand off

1. Run a final reconciliation checklist from the prepared-file counts, exception counts, and MySQL counts through analytical views, API totals, and Power BI cards. Use raw counts only as an immutable source baseline.
2. Verify that the eight date corrections, one derived approval imputation, one retained zero payment, and ten retained zero freight values are traceable from the prepared files through MySQL, API, analytics, and reporting; use raw data only for provenance and confirm the source approval null remains unchanged.
3. Test report refresh from the governed source and record refresh duration, failures, latest purchase date, and validation results.
4. Configure workspace permissions, gateway/connection settings, scheduled refresh, and row-level security only if required by the deployment context.
5. Publish the report and its data source with a version number, preprocessing batch ID, model version, and refresh timestamp.
6. Deliver the README, data dictionary, relationship diagram, metric definitions, null-handling decision log, preprocessing and load logs, exception report, API documentation, test results, and Power BI report link/file.
7. Record known limitations, including delivered-only status coverage, non-random repeat-customer sampling, eight invalid lifecycle sequences corrected in prepared data, one approval timestamp imputed only for analysis, and CLV data sufficiency concerns.

### Step 11 — Set up the future-data pipeline

1. Define the arrival contract for future files: expected filenames/columns, batch ID, delivery location, encoding, date coverage, and checksum.
2. Land every new delivery in a versioned raw-data folder without overwriting previous batches.
3. Run the Step 2 and Step 3 Pandas/NumPy preprocessing and validation automatically. Read and version `null_handling_decisions.csv` with each batch. Include row counts, datetime conversion, deterministic lifecycle-date correction, decision-file-driven null handling, key/composite-key checks, foreign-key coverage, review-score domains, numeric domains, zero-value checks, and audit-file creation. Impute only approved derived analysis fields; preserve source nulls; retain valid zero payment/freight values with zero imputation/deletion counts.
4. Stop the pipeline when schema, key, type, relationship, or decision-log validation fails. Apply the documented lifecycle-date boundary corrections and approval-imputation decision consistently, retain source-date/source-null audit fields, verify zero remaining analysis approval nulls, confirm zero payment/freight rows were neither imputed nor deleted, and keep environment-specific file-write failures separate from data-quality status.
5. Load only approved prepared data from `data/prepared/` into MySQL using the approved direct table-import procedure (MySQL Workbench Table Data Import Wizard for manual batches). Keep a staging area, batch record, and quarantine path for rejected rows; use SQLAlchemy/PyMySQL for application and analytical access after loading.
6. Run post-load reconciliation and refresh the analytical MySQL views/tables or controlled Pandas extract, preserving exception flags and separate item/payment grains.
7. Refresh the Power BI semantic model from the governed MySQL source or extract. Do not refresh from an unvalidated raw folder.
8. Run Power BI refresh validation: row counts, latest date, order/customer totals, item revenue, freight, payment totals, exception counts, and key report cards must reconcile to MySQL.
9. Publish or promote the refreshed report only after validation succeeds; record batch ID, source version, preprocessing status, refresh time, status, and failure details.
10. Add retry, alerting, and rollback procedures so a failed preprocessing, MySQL load, or Power BI refresh does not replace the last known-good report.

Pipeline sequence:

```text
New raw files
    -> version/checksum/register batch
    -> Pandas + NumPy pre-load validation and exception review
    -> prepared-file and exception-artifact verification
    -> MySQL Workbench table-data import to MySQL
    -> SQLAlchemy/Pandas post-load EDA and analytical refresh
    -> Power BI dataset refresh
    -> reconciliation checks
    -> publish updated reports
```

Exit criteria: a new approved batch can move from raw files to refreshed Power BI visuals without manual data edits, and a failed batch leaves the previous good data/report available.

End state: a reproducible pipeline from immutable raw Olist files to validated MySQL data, tested API and analytical outputs, and refreshable Power BI reports.

## 4. Technology stack

| Layer | Technologies | Responsibility |
| --- | --- | --- |
| Programming | Python | ETL scripts, services, API, analytics |
| Numerical computing | NumPy | Numeric conversion, calculations, and analytical features |
| Data engineering | Pandas | CSV ingestion, validation, joins, aggregation, and extracts |
| Visualization | Matplotlib, Seaborn | Exploratory analysis and validation charts |
| Database language | SQL | DDL, constraints, views, reconciliation queries, and analytical queries |
| Database | MySQL | Persistent relational storage and governed reporting views |
| MySQL connection / ORM | SQLAlchemy, PyMySQL | Engine, sessions, parameterized queries, ORM/Core models, and MySQL connectivity |
| API | FastAPI | REST endpoints and OpenAPI documentation |
| Validation | Pydantic | Settings, request validation, and response models |
| Reporting | Power BI | Semantic model, DAX measures, dashboards, and refreshable reports |

Important: SQLAlchemy should manage the MySQL engine, sessions, parameterized queries, and ORM/Core models through the PyMySQL driver. Raw SQL remains appropriate for DDL, views, reconciliation, and performance-sensitive queries. Pandas/NumPy own the data-preparation layer, Matplotlib/Seaborn support exploratory validation, FastAPI/Pydantic own the API contract, and Power BI consumes governed MySQL views or controlled analytical extracts.

## 5. High-level architecture

```text
Nine Olist CSV files (historical)
              |
              v
Python + Pandas + NumPy validation and ETL
              |
              v
      MySQL 8.0 OLTP schema
              ^
              |
FastAPI -> Pydantic -> Services -> SQLAlchemy -> PyMySQL -> MySQL
   |                |
   |                +--> Cohort/RFM aggregation
   |                +--> Stored CLV predictions (later)
   v
REST JSON responses / Swagger UI
              |
              +--> Power BI / analytical star schema (later)
```

Separation of concerns: Routes handle HTTP and direct parameterized SQL for this basic backend; schemas validate inputs/outputs; models define database tables; ETL is a separate repeatable process.

## 6. Database requirements and relational outline

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
| geolocation | ZIP prefix in reduced dataset | latitude, longitude, city, state | Representative lookup; one original row per referenced prefix |

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
- [ ] Document repeatable MySQL Workbench table definitions/import mappings and test restoring the last known-good database/report batch in development.

## 7. Functional requirements (FR)

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
| GET | /products | Paginated product catalog | limit, offset, category_name |
| GET | /products/{product_id} | Product detail | Path ID |
| GET | /sellers | Paginated seller catalog | limit, offset, state, city |
| GET | /sellers/{seller_id} | Seller detail | Path ID |
| GET | /category-translations | Category translations | limit, offset, category_name |
| GET | /category-translations/{product_category_name} | Category translation detail | Path name |
| GET | /geolocation | ZIP-prefix geolocation lookup | limit, offset, state, city |
| GET | /geolocation/{zip_code_prefix} | Geolocation detail | Path ZIP prefix |
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
  "total": 1208,
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

## 8. Non-functional requirements (NFR)

| ID | Area | Requirement / validation |
| --- | --- | --- |
| NFR-01 | Maintainability | Split routes, schemas, models, services, repositories, ETL and tests |
| NFR-02 | Data integrity | Transactional imports; FK constraints; idempotent/restartable ETL |
| NFR-03 | API reliability | Proper database session lifecycle; rollback on failures |
| NFR-04 | Database access | Use SQLAlchemy engine/session lifecycle, PyMySQL connectivity, parameterized queries, explicit transactions, connection cleanup, and a least-privilege MySQL account |
| NFR-05 | Connection safety | Configure pool_pre_ping=True; tune pool limits for environment |
| NFR-06 | Query efficiency | Index lookups, pagination, eager-loading, avoid unnecessary joins |
| NFR-07 | Security | Secrets in .env (excluded from Git); restricted CORS origins; least-privilege DB credentials |
| NFR-08 | Observability | Structured logs, error tracking, health endpoint, ETL run summaries |
| NFR-09 | Testing | Unit, API integration, data reconciliation and negative tests |
| NFR-10 | Reproducibility | Dependency versioning, README, versioned data dictionary/import mappings, deterministic Pandas extracts, and recorded Power BI source/refresh settings |
| NFR-11 | Performance | Measure response times and throughput; do not assert fixed SLAs without measurements |
| NFR-12 | Analytics correctness | Stable observation cutoff, no future-data leakage, consistent order-status rules |

Async session note: Use a fresh AsyncSession per request/task; do not share a session concurrently. expire_on_commit=False is recommended for async ORM usage. CPU-heavy model fitting should run outside the request's event loop, for example in a batch job.

CORS note: CORS is a browser enforcement mechanism, not a substitute for authentication or authorization. The Power BI desktop/connector integration may not depend on browser CORS in the same way as a JavaScript frontend.

## 9. Analytics definitions and business rules

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
10. RFM model units: Use one time unit consistently (days/weeks/months); frequency means repeat purchases, not all purchases.

### Cohort calculation example (illustrative only)

| Cohort | Customers acquired | Month 0 | Month 1 | Month 2 |
| --- | --- | --- | --- | --- |
| 2017-01 | 100 | 100% | 20% | 12% |
| 2017-02 | 80 | 100% | 25% | 10% |

These numbers are examples, not computed from the user's subset.

## 10. CLV model requirements (advanced phase)

The research proposes a two-model probabilistic approach, but `lifetimes` is not part of the selected stack. Treat probabilistic CLV as optional until an approved dependency is added and validated. The stack-compatible baseline is descriptive RFM and cohort analysis using SQL, Pandas, and NumPy:

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

Critical limitation: The 1,500-row-cap subset was intentionally selected to favor repeat buyers. It is useful for exercising the code but may bias CLV estimates and provide inadequate training/holdout samples. The final subset has 1,208 orders and 380 repeat customers, but that does not guarantee enough chronological history for a reliable model. If models fail to fit, complete the descriptive RFM and cohort MVP first; do not fabricate predictions.

Profit vs revenue: Olist price/payment data do not directly establish customer profit margins. Unless actual margin/cost data are supplied, label forecasts as revenue-based CLV, not lifetime profit.

## 11. Suggested codebase structure

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

This is a proposed future structure and must not be confused with the implemented tree. The actual backend tree is documented in [`step_7_fastapi_backend.md`](./step_7_fastapi_backend.md).

For the implemented backend, keep ORM models in separate files under `backend/models/` and keep API response schemas in separate files under `backend/schemas/`. The catalog API uses `schemas/catalog.py` for Product, Seller, CategoryTranslation, and Geolocation responses. The catalog endpoints should remain read-only and use the existing loaded MySQL tables.

## 12. Implementation outline and milestone deliverables

### Phase 0 — Business understanding and dataset inspection

- Confirm 1,500-cap subset, all nine files and final row counts.
- Choose eligible order statuses and monetary definitions.
- Inspect keys, duplicates, missing dates and customer identity.
- Deliverable: data dictionary, relationship diagram, business-rule notes.

### Phase 1 — Prepared data and MySQL table import

- Prepare and validate the data with Pandas and NumPy.
- Create destination tables in MySQL Workbench or select existing tables.
- Import each prepared CSV with the MySQL Workbench Table Data Import Wizard.
- Record table/column/type mappings, row counts, warnings, and failures.
- Use SQLAlchemy/PyMySQL only for later application and analytical access.
- Verify row counts, foreign keys, sample joins and sums.
- Deliverable: populated MySQL tables, import evidence, and reconciliation report.

### Phase 2 — Core FastAPI backend (MVP)

- Initialize app, settings, DB session dependency and /docs.
- Build customers/orders listing and detail routes.
- Add Product, Seller, CategoryTranslation, and Geolocation catalog schemas and read-only endpoints.
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

- Package the Python/FastAPI application and MySQL setup with documented local-run instructions.
- Run focused API and SQL performance checks; record measured latency and error results if performance claims are made.
- Add environment setup, schema, API examples, known limitations and screenshots to README.
- Deliverable: reproducible portfolio project and test evidence.

## 13. Backend MVP acceptance checklist

- [ ] FastAPI application starts with the selected local FastAPI server command.
- [ ] /docs displays documented endpoints.
- [ ] MySQL connection works with configured credentials.
- [ ] MySQL Workbench table imports create/load all required tables, or exceptions are documented.
- [ ] All nine CSVs are imported or exceptions documented.
- [ ] Order, customer, item, payment and review relationships reconcile.
- [ ] Product, seller, category translation, and geolocation catalog endpoints reconcile with ORM/database rows.
- [ ] Customer history uses customer_unique_id.
- [ ] Customer and order listing APIs return deterministic paginated results.
- [ ] Order detail includes related records without duplicate totals.
- [ ] Invalid input returns 422 and unknown records return 404.
- [ ] A failed database operation does not leave a SQLAlchemy session/connection open or corrupt the transaction.
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

## 14. Risks, caveats and open decisions

| Topic | Risk / decision to resolve |
| --- | --- |
| Reduced dataset | Repeat-customer oversampling biases population-level insights |
| Small sample | CLV models may not converge or generalize |
| Customer IDs | customer_id vs customer_unique_id changes retention calculations |
| Revenue | price, freight_value, and payment_value measure different things |
| Order status | Canceled/undelivered orders affect metrics; define inclusion policy |
| Reviews | Check uniqueness of review_id and join cardinality |
| Geolocation | Reduced ZIP-prefix file is a representative lookup, not the full original observation set |
| Model evaluation | Historical holdout must respect chronology; avoid data leakage |
| Power BI | Research presents both API ingestion and direct MySQL/read-replica ingestion; select and document one primary route |
| Deployment | Gunicorn/worker setup and reverse proxy are later-stage choices, not required for local development |
| Security | CORS does not authenticate API users; add authorization if data exposure requires it |

### Recommended build order

Start with: business questions → raw-data acquisition → data understanding → Pandas/NumPy preprocessing → MySQL Workbench table import → post-load QA/EDA → analytical metrics.
Then add: FastAPI customer/order endpoints → tests → Power BI semantic model/reports → refresh validation and future-batch pipeline.

This order delivers a demonstrable FastAPI + MySQL project even if the advanced CLV model is not viable on the reduced dataset.

## 15. Research alignment and verified references

### Materials provided in this conversation

- Research report: Strategic Analysis of Integrated Data Analytics and Python Backend Engineering Projects (15 project ideas, top-ranked e-commerce engine).
- Research report: Comprehensive Pre-Project Checklist and Data Architecture for an Enterprise E-Commerce Cohort and Customer Lifetime Value Engine.
- Research report: Enterprise E-Commerce Cohort and Customer Lifetime Value Engine: A Comprehensive Project Blueprint.
- User's ten-category project checklist and the previously generated comprehensive Markdown blueprint.
- `data/raw/olist_trimmed_1500_relational/README_RELATIONSHIPS.md` (selection, joins, and subset caveats).
- `data/raw/olist_trimmed_1500_relational/validation_report.json` (final row counts and validation results).

### External documentation checked for technical compatibility

- FastAPI — SQL (Relational) Databases: FastAPI supports SQL databases including MySQL and does not require a particular ORM.
- Olist Brazilian E-Commerce Dataset: original dataset download and description.
- [IBM CRISP-DM guide](https://www.ibm.com/docs/en/SS3RA7_19.0.0/pdf/ModelerCRISPDM.pdf): business understanding, data understanding, data preparation, modeling, evaluation, and deployment as an iterative lifecycle.
- [MySQL Workbench Table Data Import Wizard](https://dev.mysql.com/doc/workbench/en/wb-admin-export-import-table.html): CSV import into a new or existing table with destination, column, type, separator, and encoding configuration.
- [Microsoft Power BI star-schema guidance](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema): consistent-grain fact tables, dimensions for filtering/grouping, and measures for summarization.
- [Microsoft Power BI refresh guidance](https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-data): refresh queries the underlying source and updates the semantic model and dependent report visuals; source schema changes require care.

Final note: This document now combines verified current implementation facts with future requirements. The database load, FastAPI API, Step 6 analytical extracts, and nine-page Power BI report are implemented. Predictive CLV, authentication, production deployment, and performance benchmarks remain future work unless separately evidenced.
