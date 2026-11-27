# SQL Folder Reference

This document describes the complete current contents of the project’s [SQL/](../SQL/) folder and the full purpose of [step6_post_load_analysis.sql](../SQL/step6_post_load_analysis.sql).

## 1. Folder contents

```text
SQL/
└── step6_post_load_analysis.sql
```

The folder currently contains one SQL file and no subfolders, stored procedures, views, migrations, schema-creation scripts, or database-seed files.

## 2. `step6_post_load_analysis.sql`

### What the file is

`step6_post_load_analysis.sql` is the manual SQL version of the project’s Step 6 post-load quality assurance, exploratory data analysis, and analytical checks.

It is written for MySQL and targets the `ecommerce` database. The script contains 12 independent read-only queries. It does not create or modify tables, insert rows, update values, delete data, create views, or refresh Power BI.

### Why the file is needed

The script provides a transparent, manually executable way to verify the loaded MySQL database and reproduce core analytical checks without running the Python pipeline. It is useful for:

- confirming that the expected tables contain rows;
- checking the order-status population;
- checking missing key and timestamp values;
- finding orphan relationships;
- calculating delivered-order revenue and freight;
- producing monthly sales summaries;
- ranking categories;
- checking customer-level RFM inputs;
- counting repeat customers;
- calculating cohort activity by month number;
- summarizing delivery duration.

The repeatable future-batch workflow is still the Python post-load pipeline. This SQL file is best used for manual investigation, database QA, reconciliation, and troubleshooting.

### Database and business assumptions

The header comments establish these rules:

- Database: `ecommerce`.
- Eligible population for realized-sales analytics: orders with `order_status = 'delivered'`.
- Person-level customer identity: `customer_unique_id`.
- Monetary values: Brazilian reais (BRL).

The script begins with:

```sql
USE ecommerce;
```

All subsequent unqualified table names are resolved in that database.

## 3. Tables used by the script

The script reads these MySQL tables:

| Table | Used by | Role |
|---|---|---|
| `orders` | Queries 1–12 | Order status, lifecycle dates, customer link, purchase dates, delivery dates, and order population. |
| `customers` | Queries 4, 7, 9, 10, 11 | Customer record-to-person mapping and customer identity. |
| `order_items` | Queries 1, 5, 6, 7, 8, 9 | Item quantities, product/seller links, item prices, and freight. |
| `payments` | Query 1 | Payment table row-count check. The script does not calculate payment totals. |
| `reviews` | Query 1 | Review table row-count check. The script does not analyze review scores. |
| `products` | Queries 5 and 8 | Product referential-integrity check and category lookup. |
| `sellers` | Query 5 | Seller referential-integrity check. |
| `category_translation` | Query 8 | English category labels where available. |

The expected database tables are populated from the prepared files under [data/prepared/](../data/prepared/), after the preparation and manual MySQL import workflow described in [future_batch_data_runbook.md](./future_batch_data_runbook.md).

## 4. Query-by-query explanation

### Query 1: Count rows in main transactional tables

```sql
SELECT 'orders' AS table_name, COUNT(*) AS row_count FROM orders
UNION ALL
...
```

#### What it contains

The query returns one row for each of these tables:

- `orders`
- `customers`
- `order_items`
- `payments`
- `reviews`

The output columns are:

| Column | Meaning |
|---|---|
| `table_name` | Hard-coded name of the table being counted. |
| `row_count` | Total physical rows in that table. |

#### Why it is needed

It is the first post-load smoke test. It confirms that the main transactional tables are populated and provides a quick comparison against the prepared-file and load-QA row counts.

#### Interpretation

The current expected counts are approximately:

- `orders`: 1,208
- `customers`: 1,208
- `order_items`: 1,500
- `payments`: 1,303
- `reviews`: 1,298

The query counts all rows and does not check uniqueness or referential integrity. Those checks are handled by later queries.

### Query 2: Check order statuses

```sql
SELECT order_status, COUNT(*) AS order_count
FROM orders
GROUP BY order_status
ORDER BY order_count DESC;
```

#### What it contains

It groups the `orders` table by `order_status` and returns:

| Column | Meaning |
|---|---|
| `order_status` | Status value stored on the order. |
| `order_count` | Number of orders with that status. |

#### Why it is needed

The project’s realized-sales and most analytical calculations use delivered orders. This query confirms the available status values and whether the expected delivered population exists.

#### Interpretation

The result is sorted from the most common status to the least common status. It does not force the population to delivered; it only reports what is present.

### Query 3: Check missing values in key order columns

```sql
SELECT
    SUM(order_id IS NULL) AS missing_order_id,
    SUM(customer_id IS NULL) AS missing_customer_id,
    SUM(order_status IS NULL) AS missing_order_status,
    SUM(order_purchase_timestamp IS NULL) AS missing_purchase_timestamp
FROM orders;
```

#### What it contains

It returns one summary row with four missing-value counts:

| Column | Meaning |
|---|---|
| `missing_order_id` | Number of orders without an order identifier. |
| `missing_customer_id` | Number of orders without a customer-record identifier. |
| `missing_order_status` | Number of orders without a status. |
| `missing_purchase_timestamp` | Number of orders without a purchase timestamp. |

The MySQL boolean expression `column IS NULL` evaluates to 1 or 0, and `SUM` counts the true values.

#### Why it is needed

These fields are required for most joins, filtering, time-series analysis, and order-level calculations. Missing values could cause records to disappear from joins or produce incomplete metrics.

#### Limitation

This query checks only four order columns. It is not a complete null audit of every column in every table. The preparation artifacts under `data/quality/` contain broader null-handling evidence.

### Query 4: Check order-to-customer relationships

```sql
SELECT COUNT(*) AS orphan_order_customer_rows
FROM orders o
LEFT JOIN customers c ON c.customer_id = o.customer_id
WHERE c.customer_id IS NULL;
```

#### What it contains

It returns one count:

| Column | Meaning |
|---|---|
| `orphan_order_customer_rows` | Orders whose `customer_id` does not match any customer record. |

#### Why it is needed

An order without a customer record cannot be reliably attributed to a person, geographic customer segment, or unique customer. The left join keeps orphan orders visible instead of dropping them.

#### Expected result

The expected result is 0 for a valid load.

### Query 5: Check item relationships

```sql
SELECT
    SUM(o.order_id IS NULL) AS orphan_orders,
    SUM(p.product_id IS NULL) AS orphan_products,
    SUM(s.seller_id IS NULL) AS orphan_sellers
FROM order_items oi
LEFT JOIN orders o ON o.order_id = oi.order_id
LEFT JOIN products p ON p.product_id = oi.product_id
LEFT JOIN sellers s ON s.seller_id = oi.seller_id;
```

#### What it contains

It validates three references from `order_items`:

| Column | Meaning |
|---|---|
| `orphan_orders` | Item rows whose `order_id` is missing from `orders`. |
| `orphan_products` | Item rows whose `product_id` is missing from `products`. |
| `orphan_sellers` | Item rows whose `seller_id` is missing from `sellers`. |

#### Why it is needed

Item revenue, category, seller, and order analytics depend on complete item relationships. Orphan item rows can cause undercounted or misattributed totals.

#### Expected result

All three counts should be 0.

### Query 6: Calculate delivered-order item and freight values

```sql
SELECT
    oi.order_id,
    ROUND(SUM(oi.price), 2) AS item_revenue,
    ROUND(SUM(oi.freight_value), 2) AS freight_collected,
    ROUND(SUM(oi.price + oi.freight_value), 2) AS item_plus_freight
FROM order_items oi
INNER JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY oi.order_id
ORDER BY item_plus_freight DESC;
```

#### What it contains

It returns one row per delivered order with:

| Column | Meaning |
|---|---|
| `order_id` | Delivered order identifier. |
| `item_revenue` | Sum of item prices for that order in BRL. |
| `freight_collected` | Sum of freight values for that order in BRL. |
| `item_plus_freight` | Sum of item price plus freight in BRL. |

#### Why it is needed

It creates an order-level revenue summary and keeps item revenue and freight separate before showing their combined value. This supports order-fact reconciliation and prevents mixing freight with product revenue.

#### Interpretation

The output is sorted from the largest to the smallest `item_plus_freight` value. Valid zero-freight rows remain zero; they are not treated as missing.

### Query 7: Calculate monthly delivered-order sales

```sql
SELECT
    DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS purchase_month,
    COUNT(DISTINCT o.order_id) AS order_count,
    COUNT(DISTINCT c.customer_unique_id) AS unique_customers,
    ROUND(SUM(oi.price), 2) AS item_revenue,
    ROUND(SUM(oi.freight_value), 2) AS freight_collected
...
```

#### What it contains

It returns one row per purchase month for delivered orders:

| Column | Meaning |
|---|---|
| `purchase_month` | Purchase month formatted as `YYYY-MM`. |
| `order_count` | Distinct delivered orders purchased in that month. |
| `unique_customers` | Distinct person-level customers associated with those orders. |
| `item_revenue` | Sum of item prices for the month in BRL. |
| `freight_collected` | Sum of freight values for the month in BRL. |

#### Why it is needed

It supports monthly sales trend analysis and provides a SQL reconciliation point for the Python-generated `order_fact_step6.csv` and monthly sales outputs.

#### Important join behavior

The query joins order items at item grain. `COUNT(DISTINCT order_id)` and `COUNT(DISTINCT customer_unique_id)` protect counts from item-row duplication. The monetary sums intentionally sum item-level values because each item row represents one contribution.

### Query 8: Find top product categories by delivered item revenue

```sql
SELECT
    COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category_name,
    COUNT(*) AS item_count,
    ROUND(SUM(oi.price), 2) AS item_revenue
...
ORDER BY item_revenue DESC
LIMIT 10;
```

#### What it contains

It returns the ten highest-revenue delivered categories:

| Column | Meaning |
|---|---|
| `category_name` | English category label when available, otherwise the original category, otherwise `unknown`. |
| `item_count` | Number of delivered item rows in the category. |
| `item_revenue` | Sum of delivered item prices in BRL. |

#### Why it is needed

It identifies the categories contributing most item revenue and provides a direct SQL check for the category visuals in the Power BI report and FastAPI analytics endpoint.

#### Join behavior

Products are joined to `category_translation` with a left join so untranslated categories remain in the output. Only delivered orders are included.

### Query 9: Build customer-level RFM inputs

```sql
SELECT
    c.customer_unique_id,
    DATEDIFF('2018-08-28', MAX(o.order_purchase_timestamp)) AS recency_days,
    COUNT(DISTINCT o.order_id) AS frequency_orders,
    ROUND(SUM(oi.price + oi.freight_value), 2) AS monetary_value
...
```

#### What it contains

It returns one row per person-level customer:

| Column | Meaning |
|---|---|
| `customer_unique_id` | Person-level customer identifier. |
| `recency_days` | Whole calendar days between the observation cutoff, `2018-08-28`, and the customer’s latest delivered purchase. |
| `frequency_orders` | Number of distinct delivered orders for the customer. |
| `monetary_value` | Sum of item price plus freight across the customer’s delivered orders in BRL. |

#### Why it is needed

It produces the raw customer-level inputs required for RFM analysis:

- recency measures how recently the person purchased;
- frequency measures how often the person purchased;
- monetary value measures the realized item-plus-freight value.

#### Limitation

This query does not calculate R, F, or M quartile scores or named segments. Those are added by the Python Step 6 analysis and represented in `data/analytics/rfm_step6.csv`.

### Query 10: Count repeat customers

```sql
SELECT COUNT(*) AS repeat_customer_count
FROM (
    SELECT c.customer_unique_id
    ...
    HAVING COUNT(DISTINCT o.order_id) > 1
) repeat_customers;
```

#### What it contains

It returns one value:

| Column | Meaning |
|---|---|
| `repeat_customer_count` | Number of people with more than one delivered order. |

#### Why it is needed

It validates repeat-customer logic using the person-level key rather than counting repeated source customer records. This is an important control for customer retention, cohort, and RFM analysis.

#### Expected result

The current subset contains approximately 380 repeat customers.

### Query 11: Calculate monthly cohort retention

```sql
WITH customer_orders AS (...), first_purchase AS (...)
SELECT
    f.cohort_month,
    TIMESTAMPDIFF(MONTH, f.cohort_month, co.purchase_month) AS month_number,
    COUNT(DISTINCT co.customer_unique_id) AS retained_customers
...
```

#### What it contains

The query uses two common table expressions:

1. `customer_orders` creates distinct person/month purchase rows for delivered orders.
2. `first_purchase` assigns each person to the earliest purchase month, which becomes the cohort month.

The final output contains:

| Column | Meaning |
|---|---|
| `cohort_month` | Customer’s first delivered purchase month, represented as the first day of the month. |
| `month_number` | Number of months elapsed since the cohort month. Month 0 is the starting month. |
| `retained_customers` | Distinct customers from the cohort active in that month number. |

#### Why it is needed

It provides a transparent SQL version of cohort activity and retention counts. It shows whether customers from an initial cohort continue to place delivered orders in later months.

#### Limitation

This query does not return `cohort_size` or `retention_rate`. The Python analytical pipeline adds those fields by joining month-zero cohort sizes and calculating:

```text
retention_rate = retained_customers / cohort_size * 100
```

### Query 12: Summarize delivery time

```sql
SELECT
    ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)), 2) AS average_delivery_days,
    MIN(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)) AS minimum_delivery_days,
    MAX(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)) AS maximum_delivery_days
FROM orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL;
```

#### What it contains

It returns one summary row:

| Column | Meaning |
|---|---|
| `average_delivery_days` | Average whole-calendar-day difference from purchase to customer delivery, rounded to two decimal places. |
| `minimum_delivery_days` | Minimum whole-calendar-day delivery difference. |
| `maximum_delivery_days` | Maximum whole-calendar-day delivery difference. |

#### Why it is needed

It provides a fast operational delivery summary and a manual check for the delivery page in the Power BI report.

#### Important difference from Python

MySQL `DATEDIFF` counts calendar-day boundaries and discards time-of-day precision. The Python analytics pipeline calculates elapsed seconds and divides by 86,400, then rounds to two decimals. The SQL and Python averages can therefore differ slightly. They are related checks, not necessarily identical calculations.

## 5. What the script does not cover

The SQL file intentionally does not:

- create or alter the database schema;
- import prepared CSV files;
- validate every column in every table;
- calculate payment totals or payment reconciliation;
- analyze review-score distributions;
- calculate on-time delivery rate against estimated delivery dates;
- generate RFM component scores or RFM segments;
- calculate cohort size and retention percentage in the final result;
- generate delivery-level detail rows;
- create the CLV transaction extract;
- write analytics CSVs;
- update the Power BI report.

Those responsibilities are handled by the preparation files, Python notebooks/scripts, and Power BI report described in the project documentation.

## 6. Relationship to the Python pipeline

The SQL script and Python pipeline overlap in analytical purpose but differ in operational role.

| Area | SQL script | Python post-load pipeline |
|---|---|---|
| Execution | Manual in MySQL Workbench or MySQL CLI. | Repeatable command-line workflow. |
| Database effect | Read-only. | Read-only from MySQL; writes analytics/quality files. |
| Row validation | Basic counts, nulls, and selected orphan checks. | Fail-fast validation and saved run status. |
| RFM | Raw recency/frequency/monetary inputs. | Component scores and descriptive segments. |
| Cohorts | Cohort month, month number, retained customers. | Adds cohort size and retention rate. |
| Delivery | Aggregate minimum/average/maximum using `DATEDIFF`. | Detailed delivery extract using timestamp duration. |
| Outputs | Query result grids only. | CSV analytics extracts and JSON/CSV quality outputs. |
| Power BI hand-off | No automatic hand-off. | Leaves updated files ready for manual Power BI refresh. |

The repeatable future-batch process is documented in [future_batch_data_runbook.md](./future_batch_data_runbook.md). The backend and report consume the generated data described in [data_folder_reference.md](./data_folder_reference.md) and [reports_folder_reference.md](./reports_folder_reference.md).

## 7. How to run the SQL script

### MySQL Workbench

1. Start MySQL.
2. Confirm the `ecommerce` database and the loaded tables exist.
3. Open [step6_post_load_analysis.sql](../SQL/step6_post_load_analysis.sql) in MySQL Workbench.
4. Select or confirm the `ecommerce` connection.
5. Execute the full script or run individual queries one at a time.
6. Review the result grid for row counts, orphan counts, revenue, RFM, cohort, and delivery checks.

### MySQL command-line client

From the project root, run:

```powershell
mysql -u <username> -p -h <host> -P <port> ecommerce < SQL\step6_post_load_analysis.sql
```

The command prompts for the password. Do not place the password directly in the command or commit credentials to the project.

### Result interpretation checklist

Before treating the database as ready for reporting, confirm:

- main table counts match the prepared/load-QA counts;
- expected delivered orders are present;
- missing key/timestamp counts are understood;
- orphan order/customer count is zero;
- orphan order/product/seller counts are zero;
- delivered item revenue and freight are plausible;
- monthly results cover the expected purchase months;
- top categories reconcile with the report’s category view;
- repeat-customer count uses `customer_unique_id`;
- cohort month numbers begin at zero;
- delivery timestamps are available for the intended population.

## 8. Safety and operational notes

- The script is read-only, but it should still be run against the intended database connection because `USE ecommerce` selects the target schema for all queries.
- Run it after the prepared data has been appended to MySQL, not before.
- Do not use it as a replacement for the Python post-load pipeline when updated analytics files are required.
- Do not interpret the selected subset as representative of the full Olist dataset.
- Keep amounts in BRL and preserve the distinction between item revenue, freight, payments, and combined item-plus-freight value.
- Preserve the person-level distinction between `customer_unique_id` and source record-level `customer_id`.
