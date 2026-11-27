"""Create Step 3 prepared files without changing the immutable raw CSVs."""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "olist_trimmed_1500_relational"
PREPARED_DIR = PROJECT_ROOT / "data" / "prepared"
QUALITY_DIR = PROJECT_ROOT / "data" / "quality"

# Approved null-handling decision: preserve the source null and impute only a
# derived analysis value for the specified order.
APPROVED_APPROVAL_IMPUTATIONS = {
    "d69e5d356402adc8cf17e08b5033acfb": pd.Timestamp("2017-02-19 01:28:47")
}

PREPARED_DIR.mkdir(parents=True, exist_ok=True)
QUALITY_DIR.mkdir(parents=True, exist_ok=True)


def read_csv(filename: str, dtype: dict[str, str] | None = None) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / filename, dtype=dtype)


orders = read_csv(
    "olist_orders_dataset.csv",
    dtype={"order_id": "string", "customer_id": "string"},
)
customers = read_csv(
    "olist_customers_dataset.csv",
    dtype={
        "customer_id": "string",
        "customer_unique_id": "string",
        "customer_zip_code_prefix": "string",
    },
)
items = read_csv(
    "olist_order_items_dataset.csv",
    dtype={
        "order_id": "string",
        "product_id": "string",
        "seller_id": "string",
    },
)
payments = read_csv(
    "olist_order_payments_dataset.csv",
    dtype={"order_id": "string"},
)
reviews = read_csv(
    "olist_order_reviews_dataset.csv",
    dtype={"review_id": "string", "order_id": "string"},
)
products = read_csv(
    "olist_products_dataset.csv",
    dtype={"product_id": "string", "product_category_name": "string"},
)

# These source fields are counts. Use integer values so CSV output contains
# `33`, not `33.0`. The import-wizard decision is to impute the 28 missing
# values with the prepared-subset medians so direct integer import succeeds.
product_attribute_count_columns = [
    "product_name_lenght",
    "product_description_lenght",
    "product_photos_qty",
]
products["product_attributes_optional_flag"] = products[
    product_attribute_count_columns
    + [
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]
].isna().any(axis=1)
products["product_attributes_imputed_flag"] = False
products["product_attributes_imputation_method"] = pd.Series(
    pd.NA, index=products.index, dtype="string"
)
for column in [
    "product_name_lenght",
    "product_description_lenght",
    "product_photos_qty",
]:
    products[column] = pd.to_numeric(products[column], errors="coerce").round().astype(
        "Int64"
    )

product_attribute_imputation_values = {
    "product_name_lenght": 52,
    "product_description_lenght": 555,
    "product_photos_qty": 1,
}
for column, value in product_attribute_imputation_values.items():
    missing = products[column].isna()
    products.loc[missing, column] = value
    products.loc[missing, "product_attributes_imputed_flag"] = True
    products.loc[
        missing, "product_attributes_imputation_method"
    ] = "prepared_subset_median"
sellers = read_csv(
    "olist_sellers_dataset.csv",
    dtype={"seller_id": "string", "seller_zip_code_prefix": "string"},
)
categories = read_csv(
    "product_category_name_translation.csv",
    dtype={"product_category_name": "string"},
)
geolocation = read_csv(
    "olist_geolocation_dataset.csv",
    dtype={"geolocation_zip_code_prefix": "string"},
)


order_date_columns = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

for column in order_date_columns:
    orders[column] = pd.to_datetime(orders[column], errors="coerce")

items["shipping_limit_date"] = pd.to_datetime(
    items["shipping_limit_date"], errors="coerce"
)
reviews["review_creation_date"] = pd.to_datetime(
    reviews["review_creation_date"], errors="coerce"
)
reviews["review_answer_timestamp"] = pd.to_datetime(
    reviews["review_answer_timestamp"], errors="coerce"
)

# Preserve source timestamps before making the minimal prepared-data correction.
orders["source_order_approved_at"] = orders["order_approved_at"]
orders["source_order_delivered_carrier_date"] = orders[
    "order_delivered_carrier_date"
]
orders["source_order_delivered_customer_date"] = orders[
    "order_delivered_customer_date"
]

orders["date_correction_flag"] = False
orders["date_correction_reason"] = pd.Series(
    pd.NA, index=orders.index, dtype="string"
)
orders["order_approved_at_missing_flag"] = orders["order_approved_at"].isna()
orders["order_approved_at_for_analysis"] = orders["order_approved_at"]
orders["order_approved_at_imputed_flag"] = False
orders["order_approved_at_imputation_method"] = pd.Series(
    pd.NA, index=orders.index, dtype="string"
)

for order_id, imputed_value in APPROVED_APPROVAL_IMPUTATIONS.items():
    selected = orders["order_id"].eq(order_id) & orders["order_approved_at"].isna()
    orders.loc[selected, "order_approved_at_for_analysis"] = imputed_value
    orders.loc[selected, "order_approved_at_imputed_flag"] = True
    orders.loc[
        selected, "order_approved_at_imputation_method"
    ] = "approved_decision_derived_analysis_value"

# Correct only the prepared copy. Boundary correction is deterministic and auditable:
# carrier cannot precede approval, and customer delivery cannot precede carrier handoff.
carrier_before_approval = (
    orders["order_approved_at_for_analysis"].notna()
    & orders["order_delivered_carrier_date"].notna()
    & (
        orders["order_delivered_carrier_date"]
        < orders["order_approved_at_for_analysis"]
    )
)
orders.loc[carrier_before_approval, "order_delivered_carrier_date"] = orders.loc[
    carrier_before_approval, "order_approved_at_for_analysis"
]
orders.loc[carrier_before_approval, "date_correction_flag"] = True
orders.loc[
    carrier_before_approval, "date_correction_reason"
] = "carrier_date_set_to_approval_date"

delivery_before_carrier = (
    orders["order_delivered_customer_date"].notna()
    & orders["order_delivered_carrier_date"].notna()
    & (
        orders["order_delivered_customer_date"]
        < orders["order_delivered_carrier_date"]
    )
)
orders.loc[delivery_before_carrier, "order_delivered_customer_date"] = orders.loc[
    delivery_before_carrier, "order_delivered_carrier_date"
]
orders.loc[delivery_before_carrier, "date_correction_flag"] = True
orders.loc[
    delivery_before_carrier, "date_correction_reason"
] = orders.loc[
    delivery_before_carrier, "date_correction_reason"
].fillna("customer_delivery_date_set_to_carrier_date")

# Optional source fields remain nullable. Flags make missingness explicit without
# changing the source meaning of null.
products["product_category_missing_flag"] = products[
    "product_category_name"
].isna()
reviews["review_comment_optional_flag"] = True

# Zero is a valid numeric value, not a missing value. Preserve it and expose flags.
payments["payment_zero_value_flag"] = payments["payment_value"].eq(0)
items["freight_zero_value_flag"] = items["freight_value"].eq(0)

# The source review_id is retained, but a stable prepared-table key is added.
reviews.insert(0, "review_record_id", range(1, len(reviews) + 1))
reviews["review_id_repeated_flag"] = reviews["review_id"].duplicated(
    keep=False
)

# Store all audit flags as numeric binary values so CSV imports can map them
# directly to MySQL BOOLEAN/TINYINT(1) columns without interpreting True/False
# as text or binary strings.
flag_columns = {
    "orders": [
        "date_correction_flag",
        "order_approved_at_missing_flag",
        "order_approved_at_imputed_flag",
    ],
    "items": ["freight_zero_value_flag"],
    "payments": ["payment_zero_value_flag"],
    "products": [
        "product_category_missing_flag",
        "product_attributes_optional_flag",
        "product_attributes_imputed_flag",
    ],
    "reviews": [
        "review_comment_optional_flag",
        "review_id_repeated_flag",
    ],
}
for dataframe_name, columns in flag_columns.items():
    dataframe = locals()[dataframe_name]
    for column in columns:
        dataframe[column] = dataframe[column].astype("int8")

prepared_files = {
    "orders_prepared.csv": orders,
    "customers_prepared.csv": customers,
    "order_items_prepared.csv": items,
    "payments_prepared.csv": payments,
    "reviews_prepared.csv": reviews,
    "products_prepared.csv": products,
    "sellers_prepared.csv": sellers,
    "category_translation_prepared.csv": categories,
    "geolocation_prepared.csv": geolocation,
}

for filename, dataframe in prepared_files.items():
    # The current MySQL Workbench wizard treats \N as text. Use the unquoted
    # NULL token for orders so nullable DATETIME fields are imported as SQL
    # NULL instead of producing an invalid datetime value.
    null_marker = "NULL" if filename == "orders_prepared.csv" else r"\N"
    dataframe.to_csv(PREPARED_DIR / filename, index=False, na_rep=null_marker)

exception_report = orders.loc[
    orders["date_correction_flag"].eq(1),
    [
        "order_id",
        "customer_id",
        "source_order_approved_at",
        "source_order_delivered_carrier_date",
        "source_order_delivered_customer_date",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "date_correction_reason",
    ],
].copy()
exception_report.insert(0, "table_name", "orders")
exception_report.insert(1, "exception_type", "date_sequence_corrected")
exception_report.to_csv(QUALITY_DIR / "date_corrections.csv", index=False)

summary = pd.DataFrame(
    [
        {"check": "prepared_order_rows", "value": len(orders)},
        {
            "check": "corrected_date_rows",
            "value": int(orders["date_correction_flag"].sum()),
        },
        {
            "check": "source_missing_approval_rows",
            "value": int(orders["order_approved_at_missing_flag"].sum()),
        },
        {
            "check": "imputed_approval_rows_for_analysis",
            "value": int(orders["order_approved_at_imputed_flag"].sum()),
        },
        {
            "check": "remaining_analysis_missing_approval_rows",
            "value": int(orders["order_approved_at_for_analysis"].isna().sum()),
        },
        {
            "check": "repeated_review_id_rows",
            "value": int(reviews["review_id_repeated_flag"].sum()),
        },
        {
            "check": "zero_payment_rows",
            "value": int(payments["payment_zero_value_flag"].sum()),
        },
        {
            "check": "zero_payment_rows_imputed",
            "value": 0,
        },
        {
            "check": "zero_freight_rows",
            "value": int(items["freight_zero_value_flag"].sum()),
        },
        {
            "check": "zero_freight_rows_imputed",
            "value": 0,
        },
    ]
)
summary.to_csv(QUALITY_DIR / "step3_preparation_summary.csv", index=False)

print(f"Prepared files written to: {PREPARED_DIR}")
print(f"Date corrections written to: {QUALITY_DIR / 'date_corrections.csv'}")
print(summary.to_string(index=False))
