# Future Batch Data Runbook

This runbook describes the repeatable process for loading a future data batch and refreshing the existing Power BI report.

```text
New raw data
    -> manual pre-MySQL analysis and preparation
    -> manual append to existing MySQL tables
    -> automated post-MySQL pipeline
    -> updated analytics files and validation results
    -> manual Power BI Refresh
    -> updated Power BI report
```

The automated post-MySQL process is implemented in [`Python/run_post_load_pipeline.py`](../Python/run_post_load_pipeline.py).

## 1. Scope and responsibilities

### Manual work before the pipeline

You are responsible for:

1. Receiving the new raw data.
2. Preserving the original raw files unchanged.
3. Checking the raw files before loading.
4. Running the existing preparation process or equivalent manual preparation.
5. Confirming that prepared files contain the required derived columns and flags.
6. Appending the prepared data to the existing MySQL tables.

### Automated work after the MySQL append

[`run_post_load_pipeline.py`](../Python/run_post_load_pipeline.py) is responsible for:

1. Connecting to the existing MySQL database.
2. Reading the existing MySQL tables.
3. Validating keys and relationships.
4. Checking for orphan records and invalid review scores.
5. Rebuilding the existing analytical outputs.
6. Writing validation and run-status files.
7. Leaving the data ready for a manual Power BI refresh.

The script does not upload raw files, prepare raw files, create missing preprocessing flags, append records to MySQL, delete or replace MySQL data, create new Power BI reporting views, or open and refresh Power BI automatically.

## 2. Before receiving a future batch

Confirm that:

- MySQL is running.
- The existing `ecommerce` database is available.
- The existing table names and columns have not changed.
- The project Python environment is available.
- The project `.env` file contains a valid `DATABASE_URL`.
- The Power BI report uses the existing configured source.
- The report file is [`Reports/Overview.pbix`](../Reports/Overview.pbix).

The `.env` file should contain a connection similar to:

```text
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/ecommerce
```

Do not commit `.env` or database passwords to Git.

## 3. Step 1 — Receive and preserve the raw data

When a new batch arrives:

1. Record the arrival date and source information.
2. Create a separate batch folder or archive location.
3. Store the original raw files there without changing their names or contents.
4. Assign a batch ID, such as `future_batch_001`.
5. Record source file names, file sizes, row counts, and data period.
6. Do not overwrite the previous raw batch.

The raw files are source evidence. Cleaning, type conversion, correction, and derived values belong in a prepared copy.

## 4. Step 2 — Perform manual pre-MySQL analysis

Before appending anything to MySQL, inspect the new raw data.

### 4.1 File and schema checks

Check that:

- All expected files are present.
- File names are correct.
- Required columns are present.
- Column names match the existing table mapping.
- Data types are compatible with the MySQL columns.
- Date fields can be parsed.
- Numeric fields contain valid numeric values.
- Text fields do not contain unexpected encoding problems.

The current preparation rules are represented in [`Python/step3_prepare_data.py`](../Python/step3_prepare_data.py). Review that file when preparing a new batch so the existing rules remain consistent.

### 4.2 Key checks

Check the keys before loading:

- `orders.order_id` is unique.
- `customers.customer_id` is unique.
- `customer_unique_id` is used for person-level customer analysis.
- Order-item uniqueness uses `(order_id, order_item_id)`.
- Payment uniqueness uses `(order_id, payment_sequential)`.
- Review rows use the prepared review-row key when source `review_id` is repeated.
- Product IDs referenced by items exist in the product data.
- Seller IDs referenced by items exist in the seller data.
- Order IDs referenced by items, payments, and reviews exist in the order data.

### 4.3 Derived flags and prepared columns

Future prepared data must contain the same fields expected by the existing MySQL tables. Examples include:

- `date_correction_flag`
- `order_approved_at_missing_flag`
- `order_approved_at_imputed_flag`
- `order_approved_at_for_analysis`
- `freight_zero_value_flag`
- `payment_zero_value_flag`
- `product_category_missing_flag`
- `product_attributes_optional_flag`
- `product_attributes_imputed_flag`
- `review_comment_optional_flag`
- `review_id_repeated_flag`

The post-MySQL pipeline does not create these preprocessing flags. They must already be present before the data is appended to MySQL. If a required flag or prepared column is missing, stop and correct the prepared data before loading it.

### 4.4 Null and correction rules

Keep the existing data rules consistent:

- Preserve source nulls where they represent actual missing source data.
- Keep source timestamps separate from derived analysis timestamps.
- Apply only approved date corrections.
- Keep valid zero payment values as zero.
- Keep valid zero freight values as zero.
- Do not replace valid zeroes with nulls.
- Do not silently delete exceptional records.
- Record rejected rows and correction decisions.

To regenerate prepared files from the current raw-data folder, run this pre-MySQL command from the project root:

```powershell
cd C:\Users\mukth\OneDrive\Desktop\E-commerce
$PythonExe = "C:\Users\mukth\OneDrive\Desktop\E-commerce\.venv\Scripts\python.exe"
& $PythonExe Python\step3_prepare_data.py
```

Review the generated files in `data/prepared/` before importing them into MySQL. This command is not part of the post-MySQL pipeline.

## 5. Step 3 — Prepare the MySQL input files

Create prepared copies of the future raw files. Do not use raw files directly as MySQL import input.

Prepared files must:

- Match the existing MySQL table schemas.
- Use the expected column names.
- Use the expected date format.
- Use the expected numeric formats.
- Use the project's nullable-value import convention.
- Include required flags and derived analysis fields.
- Preserve source values and audit fields where corrections were made.

Compare future prepared-file headers with the current files in `data/prepared/` before continuing.

For the current controlled batch, the prepared filenames are `geolocation_prepared_mysql_normalized.csv` and `reviews_prepared_mysql_binary.csv` for the MySQL-normalized geolocation and review inputs. The preparation script's historical default names should not be used as import inputs unless the generated schema and import mapping have been reviewed.

## 6. Step 4 — Manually append the prepared data to MySQL

Append only approved prepared data to the existing MySQL tables.

Recommended order:

1. Reference tables such as products, sellers, category translations, and geolocation.
2. Customers.
3. Orders.
4. Order items.
5. Payments.
6. Reviews.

Use the existing MySQL import procedure and mappings. Do not change table or column names because the existing analytics code and Power BI setup depend on them.

After the append:

1. Record the MySQL import date.
2. Record the batch ID.
3. Record rows attempted, inserted, and rejected.
4. Confirm that the append completed successfully.
5. Do not run the pipeline if the import failed or was only partially completed unless the partial state was intentionally reviewed.

## 7. Step 5 — Configure the project environment

Open a terminal in:

```text
C:\Users\mukth\OneDrive\Desktop\E-commerce
```

Use the project virtual environment:

```powershell
c:/Users/mukth/OneDrive/Desktop/E-commerce/.venv/Scripts/python.exe
```

The pipeline reads `DATABASE_URL` from `.env` and does not accept database passwords directly on the command line.

From the project root, define the Python command used below:

```powershell
cd C:\Users\mukth\OneDrive\Desktop\E-commerce
$PythonExe = "C:\Users\mukth\OneDrive\Desktop\E-commerce\.venv\Scripts\python.exe"
```

## 8. Step 6 — Run the automated post-MySQL pipeline

Run this after the prepared data has been appended to MySQL:

```powershell
c:/Users/mukth/OneDrive/Desktop/E-commerce/.venv/Scripts/python.exe Python/run_post_load_pipeline.py --batch-id future_batch_001
```

If no batch ID is supplied, the script generates one from the current UTC timestamp:

```powershell
c:/Users/mukth/OneDrive/Desktop/E-commerce/.venv/Scripts/python.exe Python/run_post_load_pipeline.py
```

The script performs this sequence:

1. Loads `.env`.
2. Reads `DATABASE_URL`.
3. Connects to MySQL.
4. Reads the existing tables without modifying them.
5. Runs post-load validation.
6. Stops if critical validation fails.
7. Converts dates and numeric fields for analysis.
8. Keeps delivered orders as the eligible population.
9. Aggregates item and payment data to order grain.
10. Builds the order-fact extract.
11. Calculates customer-level RFM metrics.
12. Calculates RFM scores and descriptive segments.
13. Calculates cohort month and retention metrics.
14. Calculates delivery-duration metrics.
15. Builds the CLV transaction extract.
16. Writes updated analytical files.
17. Writes validation results.
18. Writes final pipeline status.

Display the available pipeline options:

```powershell
& $PythonExe Python\run_post_load_pipeline.py --help
```

Run the pipeline with a recorded batch ID:

```powershell
& $PythonExe Python\run_post_load_pipeline.py --batch-id future_batch_001
```

Alternatively, allow the script to generate a timestamp-based batch ID:

```powershell
& $PythonExe Python\run_post_load_pipeline.py
```

For manual troubleshooting, open [`SQL/step6_post_load_analysis.sql`](../SQL/step6_post_load_analysis.sql) in MySQL Workbench, select the `ecommerce` database, and execute the required statements. If the MySQL command-line client is installed, use:

```powershell
mysql -u <username> -p -h <host> -P <port> ecommerce < SQL\step6_post_load_analysis.sql
```

Do not place the password in the command. The repeatable future-batch process is the Python pipeline, not manual execution of every SQL statement.

For interactive investigation, open [`Python/step6_post_load_analysis.ipynb`](../Python/step6_post_load_analysis.ipynb) with:

```powershell
& $PythonExe -m jupyter notebook Python\step6_post_load_analysis.ipynb
```

The notebook is optional and is not required for the automated pipeline. Run project tests when validating a code change:

```powershell
& $PythonExe -m pytest
```

## 9. Automated validation performed by the pipeline

The pipeline checks:

- Main table row counts.
- Duplicate order IDs.
- Orders without customers.
- Items without orders.
- Items without products.
- Items without sellers.
- Invalid review scores outside the 1–5 range.

If any relationship or quality check fails, the script raises an error and marks the run as failed. Existing analytics files are written only after validation and analysis complete successfully.

## 10. Output files

After a successful run, the pipeline updates these existing files in `data/analytics/`:

```text
data/analytics/order_fact_step6.csv
data/analytics/rfm_step6.csv
data/analytics/cohort_retention_step6.csv
data/analytics/delivery_metrics_step6.csv
data/analytics/clv_transactions_step6.csv
```

It also writes:

```text
data/quality/post_load_validation_summary.csv
data/quality/post_load_pipeline_run.json
```

The JSON run file contains the batch ID, run status, completion time, and pipeline validation/error status. Treat the CSV validation summary and the five analytics files as the authoritative detailed outputs; if a run fails, do not refresh Power BI.

Inspect the latest pipeline status and validation summary with:

```powershell
Get-Content data\quality\post_load_pipeline_run.json
Get-Content data\quality\post_load_validation_summary.csv
Get-ChildItem data\analytics -File
```

## 11. If the pipeline succeeds

The terminal should show a success message similar to:

```text
Post-load pipeline succeeded for future_batch_001
```

Before refreshing Power BI, review:

1. `data/quality/post_load_pipeline_run.json`.
2. `data/quality/post_load_validation_summary.csv`.
3. The latest order date.
4. Total order and customer counts.
5. Row counts of regenerated analytics files.
6. Changes in exception or flag counts.

Do not refresh Power BI if the pipeline status is `failed`.

## 12. Step 7 — Manually refresh Power BI

After a successful pipeline run:

1. Open [`Reports/Overview.pbix`](../Reports/Overview.pbix). From PowerShell, you can run:

   ```powershell
   Start-Process Reports\Overview.pbix
   ```

2. Confirm that the existing source connection is available.
3. Select **Home → Refresh**.
4. Wait for all queries to complete.
5. Check for refresh errors.
6. Verify the latest report date.
7. Verify order and customer totals.
8. Verify revenue, freight, payment, cohort, RFM, and delivery visuals.
9. Check that filters and relationships still work.
10. Save the refreshed PBIX file.

The Power BI refresh is manual by design. The Python pipeline prepares the existing source data; clicking **Refresh** updates the report from that source.

## 13. What happens when a run fails

If the pipeline fails:

1. Do not refresh Power BI.
2. Open `data/quality/post_load_pipeline_run.json`.
3. Read the `error` field.
4. Check the MySQL append and prepared data.
5. Correct the issue in the prepared data or MySQL load.
6. Re-run the pipeline with the same or a new batch ID after correction.
7. Refresh Power BI only after a successful run.

Common failure causes include:

- Incorrect `DATABASE_URL`.
- MySQL not running.
- Missing MySQL table.
- Changed table or column name.
- Duplicate order ID.
- Orphan item, product, seller, or customer record.
- Invalid review score.
- Missing prepared flag column.
- Partially completed MySQL append.

The pipeline does not automatically roll back a MySQL append. Correct or reverse an invalid database load using the approved database procedure before retrying.

## 14. What is not automated

The following remain manual:

- Receiving raw data.
- Pre-MySQL data analysis.
- Creating prepared files.
- Creating preprocessing flags.
- Appending data to MySQL.
- Correcting a failed MySQL import.
- Clicking Refresh in Power BI.
- Reviewing final report values.

The automated portion begins after the MySQL append and ends when updated source files and validation results are ready for Power BI.

## 15. Short repeatable checklist

- [ ] Preserve the raw files.
- [ ] Assign a batch ID.
- [ ] Perform pre-MySQL analysis.
- [ ] Prepare the data and required flags.
- [ ] Validate keys, types, dates, nulls, and relationships.
- [ ] Append prepared data to MySQL.
- [ ] Record the append result.
- [ ] Run `Python/run_post_load_pipeline.py`.
- [ ] Confirm pipeline status is `success`.
- [ ] Review validation and analytics outputs.
- [ ] Open `Reports/Overview.pbix`.
- [ ] Click **Refresh**.
- [ ] Verify the updated report.
- [ ] Save the refreshed PBIX file.
