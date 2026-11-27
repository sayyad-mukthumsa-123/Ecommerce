# Step 2 — Data Understanding and Initial Profiling

## Source and scope

This report records the observations from `Python/pre-analysis.ipynb` and compares them with the Step 2 requirements in `docs/project_outline.md`.

The analysis uses the nine raw files in `data/raw/olist_trimmed_1500_relational/`. The files are a prepared, non-random Olist subset containing delivered orders, with repeat customers intentionally prioritized. The raw files must remain unchanged.

The notebook contains saved outputs for the profiling cells. Its current notebook metadata marks the cells as not executed in the current kernel, so this report treats the saved outputs and the accompanying `README_RELATIONSHIPS.md` and `validation_report.json` as the recorded evidence.

## 1. Dataset inventory

| Table/file | Rows | Columns | Observed grain |
|---|---:|---:|---|
| `olist_orders_dataset.csv` | 1,208 | 8 | One row per order |
| `olist_customers_dataset.csv` | 1,208 | 5 | One order-linked customer record |
| `olist_order_items_dataset.csv` | 1,500 | 7 | One product line within an order |
| `olist_order_payments_dataset.csv` | 1,303 | 5 | One payment record for an order |
| `olist_order_reviews_dataset.csv` | 1,298 | 7 | One review record associated with an order |
| `olist_products_dataset.csv` | 1,096 | 9 | One product |
| `olist_sellers_dataset.csv` | 494 | 4 | One seller |
| `product_category_name_translation.csv` | 57 | 2 | One category translation |
| `olist_geolocation_dataset.csv` | 956 | 5 | One representative ZIP-prefix location |

The row counts match the project validation report. The 1,500-row limit applies per CSV and does not mean there are 1,500 customers or 1,500 orders.

## 2. Observed schemas

### Orders

Columns are `order_id`, `customer_id`, `order_status`, five order lifecycle timestamps, and `order_estimated_delivery_date`. `order_id` is the order identifier and `customer_id` links to the order-linked customer record.

### Customers

Columns are `customer_id`, `customer_unique_id`, customer ZIP prefix, city, and state. `customer_unique_id` identifies the person across orders and is therefore the correct identifier for repeat-customer, cohort, retention, RFM, and CLV analysis.

### Order items

Columns are `order_id`, `order_item_id`, `product_id`, `seller_id`, `shipping_limit_date`, `price`, and `freight_value`. The safe item key is the composite `(order_id, order_item_id)`.

### Payments

Columns are `order_id`, `payment_sequential`, `payment_type`, `payment_installments`, and `payment_value`. The safe payment key is the composite `(order_id, payment_sequential)`. Multiple payment records can belong to one order.

### Reviews

Columns are `review_id`, `order_id`, `review_score`, two comment fields, and two review timestamps. `review_id` is not unique in this subset and must not be used as the sole primary key.

### Products, sellers, categories, and geolocation

Products contain category and physical-attribute fields; sellers contain seller identity and location; the category table translates Portuguese category names to English; and geolocation provides latitude, longitude, city, and state for ZIP prefixes.

The reduced geolocation file intentionally retains one original record per referenced ZIP prefix. It is a representative lookup, not the complete original geolocation observation set.

## 3. Data types and conversion observations

The notebook loaded identifiers and timestamps as strings. Numeric observations were:

- Customer, seller, and geolocation ZIP prefixes were loaded as `int64`; they should be preserved as strings during preprocessing so leading zeroes cannot be lost.
- Order item `order_item_id` and payment `payment_sequential` were loaded as integers.
- Item `price` and `freight_value`, payment `payment_value`, and product dimensions were loaded as floating-point values.
- Payment installments and review scores were loaded as integers.
- Product attributes with missing values were loaded as floating-point values because Pandas needs a nullable representation.

All order lifecycle timestamps were converted to datetime with invalid values coerced to null. The prepared data should use explicit datetime columns in MySQL and in analytical DataFrames.

## 4. Missing-value observations

| Table | Column | Missing rows | Approx. share | Interpretation/action |
|---|---|---:|---:|---|
| Orders | `order_approved_at` | 1 | 0.08% | Preserve as nullable; investigate the single missing approval timestamp |
| Reviews | `review_comment_title` | 1,200 | 92.45% | Optional text; preserve nulls, do not replace with fabricated text |
| Reviews | `review_comment_message` | 774 | 59.63% | Optional text; preserve nulls |
| Products | `product_category_name` | 28 | 2.55% | Preserve nulls; category translation is unavailable for these rows |
| Products | `product_name_lenght` | 28 | 2.55% | Preserve nullable source attribute |
| Products | `product_description_lenght` | 28 | 2.55% | Preserve nullable source attribute |
| Products | `product_photos_qty` | 28 | 2.55% | Preserve nullable source attribute |

No missing values were observed in the customers, order items, payments, sellers, category translations, or geolocation tables.

Missingness is concentrated in optional review text and optional product attributes. These values should not be silently filled during Step 3 preprocessing.

## 5. Duplicate and key observations

No complete duplicate rows were found in any of the nine tables.

The notebook found zero duplicate values for:

- `orders.order_id`
- `customers.customer_id`
- `products.product_id`
- `sellers.seller_id`

It found 254 rows belonging to repeated `reviews.review_id` values. Therefore, `review_id` cannot be the sole primary key. The source value should be retained, while the destination table uses `review_record_id` as the safe row identifier.

The validation report additionally confirms uniqueness of:

- `(order_id, order_item_id)` in order items
- `(order_id, payment_sequential)` in payments
- Geolocation ZIP prefixes within this reduced subset
- Category names in the translation table

## 6. Date and time observations

The observed date ranges are:

| Field | Earliest | Latest |
|---|---|---|
| Order purchase | 2016-10-03 09:44:50 | 2018-08-28 10:57:13 |
| Order approved | 2016-10-06 11:43:20 | 2018-08-28 11:10:23 |
| Delivered to carrier | 2016-10-10 16:03:01 | 2018-08-28 15:26:00 |
| Delivered to customer | 2016-10-13 16:03:46 | 2018-08-30 23:38:26 |
| Estimated delivery | 2016-10-27 00:00:00 | 2018-10-25 00:00:00 |

The purchase period covers October 2016 through August 2018, with no November 2016 purchase month in the validated subset. The data spans 22 observed purchase months:

`2016-10`, `2016-12`, and `2017-01` through `2018-08`.

Monthly order counts are:

| Month | Orders |
|---|---:|
| 2016-10 | 23 |
| 2016-12 | 1 |
| 2017-01 | 93 |
| 2017-02 | 99 |
| 2017-03 | 102 |
| 2017-04 | 35 |
| 2017-05 | 48 |
| 2017-06 | 45 |
| 2017-07 | 56 |
| 2017-08 | 74 |
| 2017-09 | 58 |
| 2017-10 | 50 |
| 2017-11 | 66 |
| 2017-12 | 37 |
| 2018-01 | 63 |
| 2018-02 | 71 |
| 2018-03 | 56 |
| 2018-04 | 63 |
| 2018-05 | 53 |
| 2018-06 | 51 |
| 2018-07 | 28 |
| 2018-08 | 36 |

The highest monthly order count is March 2017 with 102 orders, followed by February 2017 with 99 and January 2017 with 93. The very small December 2016 count and the missing November 2016 month should be considered when interpreting cohort sizes.

## 7. Categorical observations

### Order status

All 1,208 orders have status `delivered`.

This means the current subset is suitable for describing delivered-order behavior, but it cannot be used to compare delivered, canceled, shipped, or unavailable order statuses. The reporting layer should still retain `order_status` and allow status filtering for future batches.

### Payment type

| Payment type | Records | Share |
|---|---:|---:|
| Credit card | 907 | 69.61% |
| Boleto | 262 | 20.11% |
| Voucher | 126 | 9.67% |
| Debit card | 8 | 0.61% |

Credit card is the dominant payment type. Payment records are not orders, so these shares describe payment rows, not necessarily the percentage of orders using each method.

### Review score

| Score | Reviews | Share |
|---:|---:|---:|
| 1 | 88 | 6.78% |
| 2 | 25 | 1.93% |
| 3 | 99 | 7.63% |
| 4 | 221 | 17.03% |
| 5 | 865 | 66.64% |

The average review score is 4.348, the median is 5, and the interquartile range is 4 to 5. Five-star reviews dominate the subset. This should be interpreted together with the fact that the dataset contains only selected delivered orders and may have review-selection effects.

## 8. Numeric observations

### Order item amounts

| Measure | Price | Freight value |
|---|---:|---:|
| Count | 1,500 | 1,500 |
| Mean | 102.6907 | 18.8708 |
| Standard deviation | 168.9467 | 12.9723 |
| Minimum | 2.90 | 0.00 |
| 25th percentile | 35.00 | 12.8250 |
| Median | 69.90 | 16.1100 |
| 75th percentile | 129.00 | 20.1025 |
| Maximum | 4,399.87 | 196.94 |

The price distribution is right-skewed: the mean is substantially higher than the median and the maximum is much larger than the upper quartile. Freight is also right-skewed, with some high-cost shipments and a minimum of zero.

### Payments

| Measure | Payment value | Installments |
|---|---:|---:|
| Count | 1,303 | 1,303 |
| Mean | 140.0335 | 3.0292 |
| Standard deviation | 207.8449 | 2.9422 |
| Minimum | 0.00 | 1 |
| 25th percentile | 49.00 | 1 |
| Median | 89.75 | 1 |
| 75th percentile | 164.4050 | 4 |
| Maximum | 4,513.32 | 21 |

Payment value is also strongly right-skewed. The zero payment value and high maximum require validation before being used in revenue or CLV calculations. Payment installments range from 1 to 21, with a median of 1.

Amounts are in Brazilian reais (BRL), according to the source documentation.

## 9. Relationship observations

The notebook found complete coverage for all 1,500 order-item rows:

- Every item `order_id` exists in the orders table.
- Every item `product_id` exists in the products table.
- Every item `seller_id` exists in the sellers table.

The validation report additionally confirms:

- Every order links to a customer.
- Every payment links to an order.
- Every review links to an order.
- Every product category has a translation when the source category is non-null.
- Every referenced customer and seller ZIP prefix has a geolocation lookup in this subset.
- Every order has at least one item, payment, and review record.

The commented-out order/customer check in the notebook should be run explicitly in Step 3 as an additional documented check, even though the validation report confirms that relationship.

## 10. Customer identity observations

The notebook found:

- 1,208 customer records
- 539 distinct `customer_unique_id` values
- 380 repeat customers according to the validation report

This confirms that multiple order-linked `customer_id` records can represent the same person. Person-level calculations must use `customer_unique_id`; `customer_id` should be used for order linkage only.

The repeat-customer count is approximately 70.50% of the 539 unique people. This high proportion is expected because the subset selection intentionally prioritized repeat buyers and must not be generalized to the full Olist population.

## 11. Initial visual profiling observations

The notebook created the following visualizations:

1. Order-status count plot — a single `delivered` bar containing all 1,208 orders.
2. Review-score count plot — a strong concentration at score 5, followed by score 4.
3. Price and freight histograms — right-skewed distributions with high-value outliers.
4. Monthly order-volume bar chart — volume is concentrated in early 2017, especially January through March, and varies across later months.
5. Missing-value pattern chart — the only missing order field shown is `order_approved_at`, with one missing row.

The saved notebook outputs are visual figures rather than tabular summaries, so the numeric observations above are the authoritative recorded values for the report.

## 12. Analytical and modeling implications

The following rules are required for the next steps:

- Keep order items and payments at separate grains. Aggregate them separately before producing order-level metrics.
- Keep `item_revenue`, `freight_collected`, and `order_payment_total` as separate measures.
- Use delivered orders for realized-sales and retention calculations in the current subset, while preserving status as an operational field.
- Use each person's first eligible purchase month as the cohort month.
- Use `customer_unique_id` for cohort, retention, RFM, and CLV calculations.
- Do not use the current data to claim representative population-level retention or CLV.
- Treat predictive CLV as an advanced, conditional phase because the subset is small, repeat-customer biased, and has limited time depth.
- Preserve all optional missing values and source identifiers during preprocessing.

## 13. Step 2 completion status

| Requirement | Status | Evidence/remaining action |
|---|---|---|
| Inspect all nine file shapes and schemas | Complete | Notebook outputs and this report |
| Inspect data types | Complete | Notebook output; ZIP prefixes need string normalization in Step 3 |
| Profile missing values | Complete | Missing-value table above |
| Check complete-row duplicates | Complete | Zero duplicates in all tables |
| Check key uniqueness | Complete with caveat | `review_id` has 254 rows belonging to repeated values; `review_record_id` is used for the destination |
| Inspect date ranges | Complete | Date table and monthly order counts |
| Inspect statuses and categories | Complete | Order status, payment type, and review-score tables |
| Profile numeric fields | Complete | Item, payment, installment, and review summaries |
| Check relationship coverage | Complete | Notebook item checks plus validation report |
| Identify table grain and key rules | Complete | Schema and relationship sections |
| Create initial visualizations | Complete | Five notebook figures |
| Record limitations and subset bias | Complete | Scope and analytical implications sections |
| Prepare data dictionary and relationship map | Ready for Step 3 | This report defines the observed structure; formal mapping can be produced during preprocessing |

## Conclusion

The raw subset is structurally consistent and fully linked for the selected delivered orders. The main data-quality issues are optional missing attributes, one missing approval timestamp, repeated review identifiers, skewed monetary values, and the intentional over-representation of repeat customers. The data is ready for Step 3 preprocessing, provided that ZIP prefixes are normalized as strings, composite keys are enforced, review identifiers are handled safely, and item/payment aggregations remain separate.
