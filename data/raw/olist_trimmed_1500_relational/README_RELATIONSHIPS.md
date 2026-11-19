# Olist real-data relational subset (maximum 1,500 rows per table)

Generated from the user-uploaded original nine CSV files. Original field names and values are preserved.

## Selection
- Delivered orders with at least one item, payment and review.
- Prefer repeat customers for cohort/CLV analysis, then spread remaining orders across purchase months.
- Include ALL original item, payment and review rows for each chosen order.
- Include referenced customer, product, seller, and category rows.
- Geolocation: retain one REAL original coordinate record for each referenced ZIP prefix (not every original geolocation observation).
- Reject candidate orders whose ZIP prefix or product category has no matching lookup in the original source.

## Keys / joins
- orders.order_id (PK); orders.customer_id -> customers.customer_id (PK).
- customers.customer_unique_id identifies repeat buyers; NOT unique per order.
- order_items (order_id, order_item_id) composite PK; -> orders.order_id, products.product_id, sellers.seller_id.
- payments (order_id, payment_sequential) composite PK; -> orders.order_id.
- reviews.order_id -> orders.order_id; reviews may be multiple per order, review_id is not assumed unique.
- products.product_category_name -> translation.product_category_name (when non-null).
- customers.customer_zip_code_prefix and sellers.seller_zip_code_prefix -> geolocation.geolocation_zip_code_prefix (unique in THIS subset).

## Caveats
- Real data can have missing values in optional fields; none have been synthesized.
- Dataset is a nonrandom, biased subset prioritizing repeat customers; DO NOT treat cohort rates or CLV as representative of the original Olist population.
- Amounts are in Brazilian reais (BRL).
- The ZIP-prefix geolocation relationship is a representative lookup, not preservation of all original coordinate observations.
- See validation_report.json for all checks and row counts.
