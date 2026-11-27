# Data Folder Reference

This document describes the complete current contents of the project’s [data/](../data/) folder. It explains the purpose of each subfolder and every file, including row counts, columns, column meanings, data preparation decisions, keys, relationships, and downstream consumers.

The data folder is the central hand-off point between the raw Olist subset, the preparation process, the MySQL database, the post-load analytics pipeline, the FastAPI backend, and the Power BI report.

## 1. Data folder architecture

```text
data/
├── raw/
│   └── olist_trimmed_1500_relational/
│       ├── original-style source CSV files
│       ├── README_RELATIONSHIPS.md
│       └── validation_report.json
├── prepared/
│   └── MySQL-ready CSV files with audit and derived columns
├── quality/
│   ├── preparation summaries
│   ├── correction and rejection evidence
│   ├── null-handling decisions
│   ├── import manifest
│   └── MySQL load QA report
└── analytics/
    ├── Step 6 analytical extracts
    └── step6_metadata.json
```

The intended data flow is:

```text
raw source files
    -> Python/step3_prepare_data.py
prepared files and quality evidence
    -> controlled MySQL import
MySQL ecommerce tables
    -> Python/run_post_load_pipeline.py
analytics CSV extracts and metadata
    -> backend/api/v1/analytics.py
FastAPI and Power BI consumers
```

The future-batch operating procedure is documented in [future_batch_data_runbook.md](./future_batch_data_runbook.md). The backend consumer is documented in [backend_folder_reference.md](./backend_folder_reference.md).

## 2. Dataset scope and important definitions

This is a selected relational subset of the Olist e-commerce dataset, not the complete original Olist population.

- Source: user-uploaded original Olist archive.
- Selection: delivered orders with items, payments, and reviews.
- Selection bias: repeat customers were prioritized, then remaining orders were spread across purchase months.
- Row limit: at most 1,500 rows per source CSV, although most tables contain fewer rows.
- Coverage: October 2016 through August 2018 for the selected orders.
- Unique people: 539 `customer_unique_id` values.
- Repeat customers: 380.
- Orders: 1,208.
- Order items: 1,500.
- Payments: 1,303.
- Reviews: 1,298.
- Monetary unit: Brazilian reais (BRL).
- Geolocation: one real source coordinate row per referenced ZIP prefix in this subset; the full original geolocation multiplicity is intentionally not retained.
- Customer identity:
  - `customer_id` identifies the customer record attached to an order.
  - `customer_unique_id` identifies the person across records and is the person-level analysis key.
- Review identity: `review_id` is not guaranteed to be unique, so prepared data adds `review_record_id` as a safe row key.
- Null policy: source missing values are preserved where they represent genuine missing data. Derived analysis fields may be populated separately when approved.

## 3. Folder: `data/raw/`

`raw/` contains the preserved source data used to construct the selected relational subset. Raw files are evidence and should not be edited in place. Preparation, type normalization, corrections, and audit fields belong in `prepared/`.

### 3.1 Folder: `data/raw/olist_trimmed_1500_relational/`

This folder contains nine relational source CSVs and two supporting metadata files. The files retain the original source field names and source values where possible.

### 3.2 `olist_customers_dataset.csv`

Contains one row for each selected source customer record associated with an order. It has 1,208 rows and 5 columns.

| Column | Meaning | Typical type / notes |
|---|---|---|
| `customer_id` | Source customer record identifier. | Text identifier; primary key in this subset. |
| `customer_unique_id` | Person-level customer identifier used to connect repeat purchases. | Text identifier; not unique across customer records. |
| `customer_zip_code_prefix` | Customer delivery ZIP-code prefix. | Text; leading zeroes must be preserved. |
| `customer_city` | Customer city. | Text; source city name. |
| `customer_state` | Brazilian state abbreviation. | Two-letter text code such as `PR`. |

### 3.3 `olist_geolocation_dataset.csv`

Contains 956 representative geolocation records for ZIP prefixes referenced by selected customers and sellers. It has 5 columns.

| Column | Meaning | Typical type / notes |
|---|---|---|
| `geolocation_zip_code_prefix` | ZIP-code prefix used as the lookup key. | Text; leading zeroes are significant. Unique within this subset. |
| `geolocation_lat` | Latitude. | Decimal geographic coordinate, approximately -90 to 90. |
| `geolocation_lng` | Longitude. | Decimal geographic coordinate, approximately -180 to 180. |
| `geolocation_city` | City associated with the ZIP prefix. | Text. |
| `geolocation_state` | Brazilian state abbreviation. | Two-letter text code. |

This is a representative lookup, not a complete copy of all original geolocation observations. A ZIP prefix can have multiple original coordinates in the full source, but this subset keeps one real source record for each referenced prefix.

### 3.4 `olist_orders_dataset.csv`

Contains the selected orders and their lifecycle timestamps. It has 1,208 rows and 8 columns.

| Column | Meaning | Typical type / notes |
|---|---|---|
| `order_id` | Order identifier. | Text; primary key. |
| `customer_id` | Customer record associated with the order. | Text; joins to `customers.customer_id`. |
| `order_status` | Current order status. | Text; selected records are delivered. |
| `order_purchase_timestamp` | Time the order was placed. | Timestamp. |
| `order_approved_at` | Time payment/order approval was recorded. | Timestamp; may be null in source. |
| `order_delivered_carrier_date` | Time the order was handed to the carrier. | Timestamp; can require sequence correction. |
| `order_delivered_customer_date` | Time the customer received the order. | Timestamp. |
| `order_estimated_delivery_date` | Estimated delivery date. | Date or timestamp depending on source representation. |

### 3.5 `olist_order_items_dataset.csv`

Contains the products and sellers attached to orders. It has 1,500 rows and 7 columns.

| Column | Meaning | Typical type / notes |
|---|---|---|
| `order_id` | Parent order identifier. | Text; joins to `orders.order_id`. |
| `order_item_id` | Sequence number of the item within the order. | Integer; combined with `order_id` forms the composite key. |
| `product_id` | Product identifier. | Text; joins to `products.product_id`. |
| `seller_id` | Seller identifier. | Text; joins to `sellers.seller_id`. |
| `shipping_limit_date` | Seller shipping deadline for the item. | Timestamp. |
| `price` | Item price. | Numeric BRL amount. |
| `freight_value` | Freight charged for the item. | Numeric BRL amount; valid zeroes represent free shipping. |

### 3.6 `olist_order_payments_dataset.csv`

Contains payment records for selected orders. It has 1,303 rows and 5 columns.

| Column | Meaning | Typical type / notes |
|---|---|---|
| `order_id` | Parent order identifier. | Text; joins to `orders.order_id`. |
| `payment_sequential` | Sequence number of the payment record within an order. | Integer; combined with `order_id` forms the composite key. |
| `payment_type` | Payment method. | Text such as `credit_card`. |
| `payment_installments` | Number of installments. | Integer; validated as positive. |
| `payment_value` | Amount represented by the payment record. | Numeric BRL amount; one zero-value payment is retained as valid. |

### 3.7 `olist_order_reviews_dataset.csv`

Contains customer reviews associated with selected orders. It has 1,298 rows and 7 columns.

| Column | Meaning | Typical type / notes |
|---|---|---|
| `review_id` | Source review identifier. | Text; not assumed unique. |
| `order_id` | Parent order identifier. | Text; joins to `orders.order_id`. |
| `review_score` | Customer rating. | Integer from 1 through 5. |
| `review_comment_title` | Optional review title. | Text; may be empty. |
| `review_comment_message` | Optional review message. | Text; may be empty. |
| `review_creation_date` | Review creation timestamp. | Timestamp. |
| `review_answer_timestamp` | Seller/platform answer timestamp. | Timestamp; may be empty. |

### 3.8 `olist_products_dataset.csv`

Contains product catalog attributes referenced by selected order items. It has 1,096 rows and 9 columns.

| Column | Meaning | Typical type / notes |
|---|---|---|
| `product_id` | Product identifier. | Text; primary key. |
| `product_category_name` | Original product category name. | Text; joins to the translation file when available. |
| `product_name_lenght` | Product-name character count. | Numeric; source spelling is retained (`lenght`). |
| `product_description_lenght` | Product-description character count. | Numeric; source spelling is retained (`lenght`). |
| `product_photos_qty` | Number of product photos. | Numeric count. |
| `product_weight_g` | Product weight in grams. | Numeric. |
| `product_length_cm` | Product length in centimetres. | Numeric. |
| `product_height_cm` | Product height in centimetres. | Numeric. |
| `product_width_cm` | Product width in centimetres. | Numeric. |

### 3.9 `olist_sellers_dataset.csv`

Contains seller records referenced by selected order items. It has 494 rows and 4 columns.

| Column | Meaning | Typical type / notes |
|---|---|---|
| `seller_id` | Seller identifier. | Text; primary key. |
| `seller_zip_code_prefix` | Seller ZIP-code prefix. | Text; joins to geolocation. |
| `seller_city` | Seller city. | Text. |
| `seller_state` | Seller Brazilian state abbreviation. | Two-letter text code. |

### 3.10 `product_category_name_translation.csv`

Contains Portuguese-to-English product category translations. It has 57 rows and 2 columns.

| Column | Meaning | Typical type / notes |
|---|---|---|
| `product_category_name` | Original category name used by products. | Text; primary/join key. |
| `product_category_name_english` | English category label. | Text; translated display value. |

### 3.11 `README_RELATIONSHIPS.md`

Documents how the raw CSVs were selected and joined. It records:

- the delivered-order and repeat-customer selection approach;
- preservation of all related item, payment, and review rows;
- the primary and composite keys;
- the foreign-key-like relationships;
- the non-unique review-ID caveat;
- the representative geolocation lookup decision;
- the warning that the subset is biased and not representative of the full Olist population.

### 3.12 `validation_report.json`

Machine-readable validation metadata for the raw relational subset. It contains:

- source and selection description;
- per-file row counts;
- primary-key and composite-key uniqueness checks;
- foreign-key and join checks;
- completeness checks for items, payments, and reviews;
- the count of unique and repeat customers;
- month coverage;
- null-preservation and geolocation/review caveats.

All listed key, join, and completeness checks are `true` for the current snapshot.

## 4. Folder: `data/prepared/`

`prepared/` contains CSVs designed for the controlled MySQL import. The files retain source data but add normalized fields, audit fields, safe keys, and preparation flags where required.

The prepared files use `\\N` as the import marker for SQL `NULL` in applicable fields. Do not treat `\\N` as an ordinary business value.

### 4.1 `category_translation_prepared.csv`

57 rows and 2 columns. It is the MySQL-ready version of the category translation lookup.

| Column | Meaning |
|---|---|
| `product_category_name` | Original category name and primary lookup key. |
| `product_category_name_english` | English translation, nullable when no translation exists. |

### 4.2 `customers_prepared.csv`

1,208 rows and 5 columns. It has the same business columns as the raw customer file, normalized for MySQL.

| Column | Meaning |
|---|---|
| `customer_id` | Customer record primary key. |
| `customer_unique_id` | Person-level customer key. |
| `customer_zip_code_prefix` | Customer ZIP prefix. |
| `customer_city` | Customer city. |
| `customer_state` | Customer state. |

### 4.3 `geolocation_prepared_mysql_normalized.csv`

956 rows and 5 columns. It is the normalized MySQL import version of the representative geolocation data.

| Column | Meaning |
|---|---|
| `geolocation_zip_code_prefix` | Unique ZIP-prefix lookup key in this subset. |
| `geolocation_lat` | Latitude. |
| `geolocation_lng` | Longitude. |
| `geolocation_city` | City. |
| `geolocation_state` | State abbreviation. |

### 4.4 `orders_prepared.csv`

1,208 rows and 17 columns. It contains source order fields plus audit-preserving and analysis-specific fields.

| Column | Meaning |
|---|---|
| `order_id` | Order primary key. |
| `customer_id` | Customer record linked to the order. |
| `order_status` | Order status. |
| `order_purchase_timestamp` | Original purchase timestamp. |
| `order_approved_at` | Prepared approval timestamp; source value unless a separate derived analysis field is needed. |
| `order_delivered_carrier_date` | Prepared carrier hand-off timestamp. |
| `order_delivered_customer_date` | Prepared customer-delivery timestamp. |
| `order_estimated_delivery_date` | Estimated delivery date. |
| `source_order_approved_at` | Original source approval timestamp retained for audit. |
| `source_order_delivered_carrier_date` | Original source carrier timestamp retained for audit. |
| `source_order_delivered_customer_date` | Original source customer-delivery timestamp retained for audit. |
| `date_correction_flag` | Indicates that an order lifecycle timestamp was corrected. |
| `date_correction_reason` | Explanation for the correction. |
| `order_approved_at_missing_flag` | Indicates that the source approval timestamp was missing. |
| `order_approved_at_for_analysis` | Complete approval timeline value used by analysis; may be imputed without overwriting the source field. |
| `order_approved_at_imputed_flag` | Indicates that the analysis approval value was imputed. |
| `order_approved_at_imputation_method` | Method used for the approval imputation. |

Current preparation facts: 8 date-sequence corrections, 1 source approval timestamp missing, 1 approval timestamp imputed for analysis, and 0 remaining analysis-missing approval values.

### 4.5 `order_items_prepared.csv`

1,500 rows and 8 columns.

| Column | Meaning |
|---|---|
| `order_id` | Parent order key. |
| `order_item_id` | Item sequence within the order; composite-key component. |
| `product_id` | Product key. |
| `seller_id` | Seller key. |
| `shipping_limit_date` | Shipping deadline. |
| `price` | Item price in BRL. |
| `freight_value` | Freight amount in BRL. |
| `freight_zero_value_flag` | Indicates a valid zero-freight row. |

Ten zero-freight rows are retained as valid free-shipping observations and were not imputed.

### 4.6 `payments_prepared.csv`

1,303 rows and 6 columns.

| Column | Meaning |
|---|---|
| `order_id` | Parent order key. |
| `payment_sequential` | Payment sequence; composite-key component. |
| `payment_type` | Payment method. |
| `payment_installments` | Installment count. |
| `payment_value` | Payment amount in BRL. |
| `payment_zero_value_flag` | Indicates a valid zero-value payment row. |

One zero-value payment is retained as valid. No zero payments were imputed.

### 4.7 `products_prepared.csv`

1,096 rows and 13 columns.

| Column | Meaning |
|---|---|
| `product_id` | Product primary key. |
| `product_category_name` | Original product category. |
| `product_name_lenght` | Product-name length; source spelling retained. |
| `product_description_lenght` | Product-description length; source spelling retained. |
| `product_photos_qty` | Photo count. |
| `product_weight_g` | Weight in grams. |
| `product_length_cm` | Length in centimetres. |
| `product_height_cm` | Height in centimetres. |
| `product_width_cm` | Width in centimetres. |
| `product_attributes_optional_flag` | Indicates optional product attributes or missing values were present. |
| `product_attributes_imputed_flag` | Indicates product attribute counts were imputed. |
| `product_attributes_imputation_method` | Imputation method, currently based on the prepared-subset median where applicable. |
| `product_category_missing_flag` | Indicates that the product category was missing. |

Twenty-eight product rows have product attribute counts imputed using the prepared-subset median method.

### 4.8 `reviews_prepared_mysql_binary.csv`

1,298 rows and 10 columns. The filename reflects the historical MySQL binary-import preparation; the QA report records that the final relevant flag columns were converted to integer values in MySQL.

| Column | Meaning |
|---|---|
| `review_record_id` | Safe unique review-row identifier generated for import. |
| `review_id` | Original source review ID, retained but not assumed unique. |
| `order_id` | Parent order key. |
| `review_score` | Score from 1 to 5. |
| `review_comment_title` | Optional review title. |
| `review_comment_message` | Optional review message. |
| `review_creation_date` | Review creation timestamp. |
| `review_answer_timestamp` | Review answer timestamp. |
| `review_comment_optional_flag` | Indicates optional review comment content. |
| `review_id_repeated_flag` | Indicates that the source review ID is repeated. |

There are 254 repeated source review-ID rows. The safe `review_record_id` prevents those rows from colliding.

### 4.9 `sellers_prepared.csv`

494 rows and 4 columns.

| Column | Meaning |
|---|---|
| `seller_id` | Seller primary key. |
| `seller_zip_code_prefix` | Seller ZIP prefix. |
| `seller_city` | Seller city. |
| `seller_state` | Seller state abbreviation. |

## 5. Folder: `data/quality/`

`quality/` contains audit evidence produced during preparation and MySQL loading. These files explain what was corrected, what was retained, what was rejected, and whether the final load passed quality checks.

### 5.1 `date_corrections.csv`

Contains 8 corrected order-date-sequence records and 11 columns.

| Column | Meaning |
|---|---|
| `table_name` | Source table affected, currently `orders`. |
| `exception_type` | Type of exception, currently date-sequence correction. |
| `order_id` | Corrected order. |
| `customer_id` | Customer linked to the order. |
| `source_order_approved_at` | Original approval timestamp. |
| `source_order_delivered_carrier_date` | Original carrier timestamp. |
| `source_order_delivered_customer_date` | Original customer-delivery timestamp. |
| `order_approved_at` | Prepared approval timestamp. |
| `order_delivered_carrier_date` | Corrected/prepared carrier timestamp. |
| `order_delivered_customer_date` | Corrected/prepared customer-delivery timestamp. |
| `date_correction_reason` | Human-readable correction rule, such as setting a carrier date to the approval date. |

The corrections make lifecycle timestamps chronological while preserving original timestamps in separate columns.

### 5.2 `load_qa_results.md`

Human-readable MySQL load QA report. It records:

- final row counts for all nine tables;
- source nulls, approval imputations, product imputations, and retained zero values;
- duplicate-key checks;
- negative amount, installment, review-score, and date-sequence checks;
- orphan relationship checks;
- the interpretation of `\\N` as SQL `NULL` during import;
- MySQL schema corrections from binary identifiers/flags to readable text or integer types.

The report states that the load passed. It records zero duplicate composite keys, zero invalid review scores, zero negative item/payment amounts, and zero orphan relationships.

### 5.3 `null_handling_decisions.csv`

Contains 12 documented data-quality decisions and 8 columns.

| Column | Meaning |
|---|---|
| `table_name` | Table containing the value. |
| `column_name` | Original column affected. |
| `row_identifier` | Row key used to identify the record. |
| `original_value` | Original value, including `NULL` or zero. |
| `handled_value` | Value retained or derived. |
| `handling_method` | Method used, such as analysis-column imputation or valid-zero retention. |
| `target_column` | Column receiving the handled value. |
| `reason` | Explanation for the decision. |

Examples include imputing one missing approval timestamp only in `order_approved_at_for_analysis`, retaining one zero payment as valid, and retaining ten zero-freight records as free shipping.

### 5.4 `rejected_rows.csv`

Contains 8 rejected or exception-tracking order rows and 10 columns.

| Column | Meaning |
|---|---|
| `table_name` | Affected table. |
| `exception_reason` | Reason the row was flagged, currently invalid date sequence. |
| `order_id` | Order identifier. |
| `customer_id` | Customer identifier. |
| `order_status` | Order status. |
| `order_purchase_timestamp` | Purchase timestamp. |
| `order_approved_at` | Approval timestamp. |
| `order_delivered_carrier_date` | Carrier hand-off timestamp. |
| `order_delivered_customer_date` | Customer-delivery timestamp. |
| `order_estimated_delivery_date` | Estimated delivery date. |

This file is an exception artifact. In the current prepared output, the relevant order records are retained with documented corrections rather than silently discarded.

### 5.5 `step3_import_manifest.json`

Machine-readable manifest for the preparation hand-off. It contains:

- `batch_id`: `STEP3-20261121-001`.
- `status`: approved for Step 4 MySQL preparation.
- source and prepared-directory paths;
- exception-artifact paths;
- each prepared filename and expected row count;
- counts for corrections, missing/imputed approvals, repeated review IDs, valid zero values, and product imputations;
- the null marker convention;
- the statement that raw files were not modified;
- the approved audit columns added during preparation.

### 5.6 `step3_preparation_summary.csv`

Contains 10 preparation checks in a simple two-column format.

| Column | Meaning |
|---|---|
| `check` | Name of the preparation metric or validation. |
| `value` | Recorded count or result. |

Current checks include prepared order rows, corrected date rows, source-missing approvals, imputed approvals, remaining analysis-missing approvals, repeated review IDs, zero-payment rows, zero-payment imputations, zero-freight rows, and zero-freight imputations.

## 6. Folder: `data/analytics/`

`analytics/` contains the Step 6 outputs consumed by the FastAPI analytics routes and used by reporting workflows. These are analytical extracts, not raw source tables.

The current batch metadata is `STEP3-20261121-001`, with delivered orders as the eligible population and an observation cutoff of `2018-08-28`.

### 6.1 `order_fact_step6.csv`

Contains one analytical row per eligible delivered order. It has 1,208 rows and 16 columns.

| Column | Meaning |
|---|---|
| `order_id` | Order identifier. |
| `customer_id` | Source customer-record identifier. |
| `order_status` | Order status used for the fact row. |
| `order_purchase_timestamp` | Purchase timestamp. |
| `order_approved_at` | Approval timestamp used in the extract. |
| `order_delivered_carrier_date` | Carrier hand-off timestamp. |
| `order_delivered_customer_date` | Customer-delivery timestamp. |
| `order_estimated_delivery_date` | Estimated delivery date. |
| `customer_unique_id` | Person-level customer key. |
| `item_count` | Number of item rows on the order. |
| `item_revenue` | Sum of item prices in BRL. |
| `freight_collected` | Sum of freight values in BRL. |
| `payment_total` | Sum of payment values in BRL. |
| `payment_count` | Number of payment records. |
| `item_plus_freight` | Item revenue plus freight. |
| `purchase_month` | Purchase month normalized to `YYYY-MM`. |

This is the order-grain analytical fact used for reconciliation and reporting. Item and payment values are pre-aggregated to avoid multiplication from one-to-many joins.

### 6.2 `rfm_step6.csv`

Contains one row per unique person-level customer used in RFM analysis. It has 539 rows and 10 columns.

| Column | Meaning |
|---|---|
| `customer_unique_id` | Person-level customer key. |
| `last_purchase` | Most recent purchase timestamp. |
| `frequency` | Number of eligible orders for the customer. |
| `monetary` | Customer monetary value in BRL. |
| `recency_days` | Days from last purchase to the observation cutoff. |
| `R_score` | Recency score from 1 to 4. |
| `F_score` | Frequency score from 1 to 4. |
| `M_score` | Monetary score from 1 to 4. |
| `RFM_score` | Sum of the three component scores, from 3 to 12. |
| `segment` | Descriptive segment: `high_value`, `regular`, `developing`, or `needs_attention`. |

This is descriptive RFM segmentation, not a predictive model.

### 6.3 `cohort_retention_step6.csv`

Contains cohort-month retention observations. It has 190 rows and 5 columns.

| Column | Meaning |
|---|---|
| `cohort_month` | Month in which the customer first entered the cohort, formatted `YYYY-MM`. |
| `month_number` | Number of months after the cohort month; 0 is the starting month. |
| `retained_customers` | Customers from the cohort active in the indicated month. |
| `cohort_size` | Number of customers in the original cohort. |
| `retention_rate` | Retained customers divided by cohort size, expressed as a percentage. |

Retention is based on the selected, repeat-customer-prioritized subset and should not be interpreted as representative of the full Olist population.

### 6.4 `delivery_metrics_step6.csv`

Contains delivery-duration metrics at order grain. It has 1,208 rows and 4 columns.

| Column | Meaning |
|---|---|
| `order_id` | Order identifier. |
| `order_purchase_timestamp` | Order purchase timestamp. |
| `order_delivered_customer_date` | Customer delivery timestamp. |
| `delivery_days` | Elapsed delivery duration in days, calculated from purchase to customer delivery. |

The values are used by `/api/v1/analytics/delivery` and reporting analyses of delivery performance.

### 6.5 `clv_transactions_step6.csv`

Contains one transaction-level row per eligible order for CLV input analysis. It has 1,208 rows and 4 columns.

| Column | Meaning |
|---|---|
| `customer_unique_id` | Person-level customer key. |
| `order_id` | Order identifier. |
| `transaction_date` | Transaction date/time, based on the order purchase timestamp. |
| `monetary_value` | Transaction monetary value in BRL. |

The file is a transaction extract only. It does not contain a fitted predictive CLV model, probability of repeat purchase, or forecast lifetime value.

### 6.6 `step6_metadata.json`

Machine-readable metadata describing the current analytics run. It contains:

- Step number: `6`.
- Batch ID: `STEP3-20261121-001`.
- Eligible status: `delivered`.
- Observation cutoff: `2018-08-28`.
- Source row counts for orders, items, and payments.
- Unique people and repeat-customer counts.
- Date correction and approval-imputation counts.
- Product count-imputation rows.
- Retained zero-payment and zero-freight counts.
- `clv_status`, explicitly stating that the output is transaction-extract-only and does not claim a probabilistic model.

## 7. Relationships between files

The raw and prepared files use the same core relational design:

```text
customers.customer_id
        |
        +--> orders.customer_id
                 |
                 +--> order_items.order_id
                 +--> payments.order_id
                 +--> reviews.order_id

order_items.product_id --> products.product_id
order_items.seller_id  --> sellers.seller_id
products.product_category_name --> product_category_name_translation.product_category_name
customers.customer_zip_code_prefix --> geolocation.geolocation_zip_code_prefix
sellers.seller_zip_code_prefix     --> geolocation.geolocation_zip_code_prefix
```

Keys:

- Orders: `order_id`.
- Customers: `customer_id`.
- Products: `product_id`.
- Sellers: `seller_id`.
- Category translation: `product_category_name`.
- Geolocation: `geolocation_zip_code_prefix` within this subset.
- Order items: `(order_id, order_item_id)`.
- Payments: `(order_id, payment_sequential)`.
- Reviews: source `review_id` is not safe as a key; prepared data uses `review_record_id`.

## 8. Quality and preparation summary

The current preparation and load evidence records:

- 1,208 prepared orders.
- 8 corrected order date sequences.
- 1 source-missing approval timestamp.
- 1 approval timestamp imputed only in the derived analysis column.
- 0 remaining analysis-missing approval timestamps.
- 254 repeated source review IDs.
- 1 valid zero-payment row retained.
- 10 valid zero-freight rows retained.
- 28 product attribute-count rows imputed using the prepared-subset median.
- 0 duplicate order-item composite keys.
- 0 duplicate payment composite keys.
- 0 duplicate safe review record identifiers.
- 0 negative item/payment amounts.
- 0 invalid payment-installment values.
- 0 invalid review scores.
- 0 invalid order-date sequences after preparation.
- 0 orphan customer, product, seller, payment, or review relationships in the load QA checks.

The raw files were not modified during preparation. The prepared files and quality artifacts are the auditable output of the preparation process.

## 9. How the data folder is consumed

### MySQL loading

The prepared CSVs are the input for the controlled MySQL load into the `ecommerce` database. The expected target tables are:

`category_translation`, `customers`, `geolocation`, `sellers`, `products`, `orders`, `order_items`, `payments`, and `reviews`.

### Post-load analytics

The post-load pipeline in [Python/run_post_load_pipeline.py](../Python/run_post_load_pipeline.py) reads the MySQL tables, validates relationships, and writes the `analytics/` extracts plus quality/run-status outputs.

### FastAPI backend

The backend uses MySQL for live summaries, monthly sales, and category performance. It reads `rfm_step6.csv`, `cohort_retention_step6.csv`, `delivery_metrics_step6.csv`, and `clv_transactions_step6.csv` for extract-backed analytics routes. See [backend_folder_reference.md](./backend_folder_reference.md).

### Power BI

The analytics files are part of the reporting data flow used by [Reports/Overview.pbix](../Reports/Overview.pbix). The future-batch procedure ends with a manual Power BI refresh after the post-load pipeline succeeds.

## 10. Safe operating rules

- Preserve everything under `raw/` unchanged.
- Do not use raw files directly as MySQL import files.
- Use `prepared/` for normalized values, flags, safe keys, and approved derived fields.
- Review `quality/` before importing or publishing a new batch.
- Treat `\\N` as the prepared-file SQL `NULL` marker where applicable.
- Preserve valid zero amounts as zero; do not convert them to null.
- Keep source timestamps and analysis timestamps in separate columns.
- Do not use `review_id` alone as a primary key.
- Do not treat this selected subset as representative of the complete Olist population.
- Do not expose the transaction extract as predictive CLV.
- Regenerate analytics outputs after a successful database append instead of manually editing analytics CSVs.
