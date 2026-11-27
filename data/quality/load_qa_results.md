# Step 5 — MySQL Load QA

Load status: **Passed**

Database: `ecommerce`

## Loaded row counts

| Table | Loaded rows |
|---|---:|
| category_translation | 57 |
| customers | 1,208 |
| geolocation | 956 |
| sellers | 494 |
| products | 1,096 |
| orders | 1,208 |
| order_items | 1,500 |
| payments | 1,303 |
| reviews | 1,298 |

## Validation results

- Source `order_approved_at` nulls: 1
- `order_approved_at_for_analysis` nulls: 0
- Approval timestamps imputed: 1
- Product attributes imputed: 28
- Zero payment rows retained: 1
- Zero freight rows retained: 10
- Duplicate order-item composite keys: 0
- Duplicate payment composite keys: 0
- Duplicate review record identifiers: 0
- Negative item/payment amounts: 0
- Invalid payment installment values: 0
- Invalid review scores: 0
- Invalid order-date sequences: 0
- Orphan orders/customers: 0
- Orphan items/orders/products/sellers: 0
- Orphan payments/orders: 0
- Orphan reviews/orders: 0

The prepared CSV files were loaded with `\\N` interpreted as SQL `NULL`. `local_infile` was enabled for the controlled load and disabled afterward.

## Schema correction

The identifier columns were initially created as `BINARY(32)`, which MySQL Workbench displayed as `BLOB`. They were converted to `TEXT` so identifiers are readable and join consistently. Row counts were unchanged, and the checked order relationships still have zero orphan rows.

The `order_items.freight_zero_value_flag` column was converted from `BINARY(1)` to `INT`. Its values were verified as `0` for 1,490 rows and `1` for 10 rows.

The product flags `product_attributes_optional_flag`, `product_attributes_imputed_flag`, and `product_category_missing_flag` were converted from `BINARY(1)` to `INT`. Their verified combined distribution is `0,0,0` for 1,068 rows and `1,1,1` for 28 rows.

The order flags `order_approved_at_imputed_flag`, `order_approved_at_missing_flag`, and `date_correction_flag` were converted from `BINARY(1)` to `INT`. Their verified combined distribution is `0,0,0` for 1,199 rows, `0,1,1` for 1 row, and `1,0,0` for 8 rows.

The `payments.payment_zero_value_flag` column was converted from `BINARY(1)` to `INT`. Its values were verified as `0` for 1,302 rows and `1` for 1 row.

The `reviews.review_comment_optional_flag` and `reviews.review_id_repeated_flag` columns were converted from `BINARY(1)` to `INT`. Their verified combined distribution is `1,0` for 1,044 rows and `1,1` for 254 rows.
