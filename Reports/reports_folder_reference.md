# Reports Folder Reference

This document describes the complete current contents of the [Reports/](../Reports/) folder and the report pages and visuals contained in [Overview.pbix](../Reports/Overview.pbix).

The report was inspected from its embedded Power BI report definition. The file contains one report artifact with nine report pages and 99 visual containers, including KPI cards, charts, slicers, and supporting analytical plots.

## 1. Folder contents

```text
Reports/
└── Overview.pbix
```

There are no source folders, scripts, CSV files, or separate page files in `Reports/`. The PBIX package contains the Power BI report definition, page definitions, visual configurations, theme resources, model data, and report metadata internally.

## 2. `Overview.pbix`

### What the file is

`Overview.pbix` is the Power BI report file for the E-commerce/Olist analytics project. It is the presentation and reporting layer built on top of the prepared MySQL data and Step 6 analytical extracts.

It contains:

- Nine report pages.
- KPI cards for business, customer, seller, product, delivery, cohort, RFM, and transaction metrics.
- Charts for trends, distributions, rankings, segmentation, relationships, and comparisons.
- Slicers for purchase month, order status, seller state, RFM score, RFM segment, cohort month, cohort month number, transaction date, and monetary value.
- Embedded report metadata and page layout definitions.
- Visual query definitions that reference model tables and the `Measures (2)` measure table.
- The embedded Power BI data model and report resources.

### Why it is needed

The PBIX file turns the project’s relational and analytical data into an interactive report for reviewing:

- overall e-commerce performance;
- order and revenue trends;
- customers and repeat-customer behavior;
- RFM customer segments;
- cohort retention;
- delivery performance;
- products and categories;
- seller performance;
- transaction-level CLV inputs.

The report is intended for interactive filtering and visual analysis. It does not replace the raw data, MySQL database, Python preparation scripts, or validation outputs.

### Report layout

All nine pages use a 1920 × 1080 canvas and `FitToPage` display mode. The report’s page order is:

1. Executive overview
2. Sales analysis
3. Customer analysis
4. Product and category analysis
5. Seller analysis
6. Delivery analysis
7. RFM analysis
8. Cohort retention
9. CLV transactions

The landing and active page are both `Executive overview`.

## 3. Data model and reporting grain

The report uses several model tables that correspond to the project’s MySQL tables and generated analytics extracts:

- `order_fact`: one row per eligible order, with customer identity, order lifecycle, item revenue, freight, payment totals, item count, payment count, and purchase month.
- `customers`: customer record identity and customer location.
- `order_items`: item-level product, seller, price, and freight data.
- `products`: product catalog attributes and category.
- `sellers`: seller identity and location.
- `category_translation`: original and English category labels.
- `delivery_metrics`: order-level delivery duration data.
- `rfm`: person-level RFM values, scores, and segment.
- `cohort_retention`: cohort month, month number, cohort size, retained customers, and retention rate.
- `clv_transactions`: one transaction-level CLV input row per order.
- `Measures (2)`: the report’s measure table containing the reusable KPI calculations referenced by cards and charts.

Important grains:

- Order measures should use `order_id` or the order-level `order_fact` table.
- Person-level customer measures should use `customer_unique_id`, not `customer_id`.
- Product and seller measures use item-level records, so item counts and revenue must be interpreted at item/order-item grain.
- RFM and cohort measures use person-level or cohort-level analytical extracts.
- CLV transactions are transaction-grain inputs, not predictive customer lifetime value.

## 4. KPI definitions

The report references measures from the `Measures (2)` table. The exact measure names are embedded in the visual definitions. The definitions below explain the business meaning and expected calculation for each measure based on the fields used by the report and the project’s analytical pipeline.

### Order and revenue KPIs

| KPI | Definition | Primary source / grain |
|---|---|---|
| `Total Orders` | Count of orders in the current filter context. When evaluated on `order_fact`, this is the count of order rows or distinct `order_id` values. | `order_fact.order_id`; order grain. |
| `Delivered Orders` | Count of orders whose order status is `delivered` in the current filter context. | `order_fact.order_status`; order grain. |
| `Delivered Order Rate` | Delivered orders divided by total orders in the current context. | `Delivered Orders / Total Orders`. |
| `Total Revenue` | Total item revenue plus freight collected for the selected order population. The report uses this on the revenue-by-status visual. | `order_fact.item_plus_freight`; order grain. |
| `Item Revenue` | Sum of product/item prices. | `order_fact.item_revenue` or item price aggregation. |
| `Freight Collected` | Sum of freight values charged on order items. | `order_fact.freight_collected` or item freight aggregation. |
| `Payment Total` | Sum of recorded payment values. | `order_fact.payment_total` or payments aggregation. |
| `Item Plus Freight` | Item revenue plus freight collected. This is the main revenue-like measure used in the executive monthly trend. | `item_revenue + freight_collected`. |
| `Payment Difference` | Difference between the recorded payment total and the item-plus-freight amount. It is useful for checking whether order payments reconcile to item revenue plus freight. | `payment_total - item_plus_freight`. |
| `Average Order Value` | Average item-plus-freight value per order in the current context. | `SUM(item_plus_freight) / DISTINCTCOUNT(order_id)`. |

Amounts are in Brazilian reais (BRL). The report should be interpreted with the selected population and slicer context in mind.

### Customer KPIs

| KPI | Definition | Primary source / grain |
|---|---|---|
| `Unique Customers` | Distinct count of `customer_unique_id`, representing people rather than source customer records. | `order_fact.customer_unique_id` or customer identity table. |
| `Repeat Customers` | Count of people with more than one eligible order in the current context. | Group delivered/order records by `customer_unique_id`. |
| `Repeat Customer Rate` | Repeat customers divided by unique customers. | `Repeat Customers / Unique Customers`. |
| `Average Orders Per Customer` | Total distinct orders divided by unique customers. | `Total Orders / Unique Customers`. |
| `New Customers` | Customers whose first eligible order falls in the current period/context. | First purchase month by `customer_unique_id`. |
| `Average Review Score` | Average of valid review scores, normally on the 1–5 scale. | `reviews.review_score`. |

`customer_id` is a source record key and should not be used as the person-level customer count when measuring unique or repeat people.

### Product and category KPIs

| KPI | Definition | Primary source / grain |
|---|---|---|
| `Total Items Sold` | Count of order-item rows in the current filter context. | `order_items`; item grain. |
| `Product Count` | Count of products represented in the current context. | `products.product_id`; product grain. |
| `Category Count` | Count of product categories represented in the current context. | Category dimension / translated category. |
| `Category Item Count` | Number of order items sold for each category. | Item rows grouped by translated category. |
| `Category Revenue` | Item revenue for each category, normally based on item price and used for category ranking and treemap contribution. | `order_items.price` grouped by category. |
| `Average Item Price` | Average item price for the selected item population. | `order_items.price`. |
| `Average Freight Per Item` | Average freight value per order-item row. | `order_items.freight_value`. |
| `Item Revenue` | Sum of item prices in the current context. | `order_items.price` or order fact. |

The report uses English translated category labels where available. Category values without a translation may remain under their original category name or an unknown/missing label depending on the model relationship.

### Seller KPIs

| KPI | Definition | Primary source / grain |
|---|---|---|
| `Seller Count` | Count of sellers represented in the current context. | `sellers.seller_id`. |
| `Seller Items Sold` | Count of order-item rows associated with each seller. | `order_items` grouped by `seller_id`. |
| `Seller Revenue` | Sum of item prices associated with a seller. | `order_items.price` grouped by seller. |
| `Seller Freight` | Sum of freight values associated with a seller. | `order_items.freight_value` grouped by seller. |
| `Average Seller Freight` | Average freight associated with the selected seller/item population. | Seller freight divided by relevant item rows or average item freight. |
| `Average Seller Order Value` | Average order value attributable to the selected seller population. | Seller-attributed value divided by relevant orders. |

Seller charts are mainly ranking and relationship views. A seller’s revenue and freight can change with purchase-month and seller-state filters.

### Delivery KPIs

| KPI | Definition | Primary source / grain |
|---|---|---|
| `Average Delivery Days` | Average elapsed days from purchase timestamp to customer-delivery timestamp. | `delivery_metrics.delivery_days`; order grain. |
| `Minimum Delivery Days` | Shortest observed delivery duration in the current context. | Minimum `delivery_days`. |
| `Maximum Delivery Days` | Longest observed delivery duration in the current context. | Maximum `delivery_days`. |
| `On-Time Delivery Rate` | Share of delivered orders where actual customer delivery is on or before the estimated delivery date. | On-time delivered orders / delivered orders. |
| `Delivered Orders` | Count of delivered orders in the delivery context. | `order_fact.order_status` or delivery table. |

Delivery duration is measured in days and is derived from order purchase to customer delivery. The report’s delivery view is intended for operational comparison, not a shipping-service-level agreement unless the estimated-date logic is explicitly adopted as the SLA definition.

### RFM KPIs

| KPI | Definition | Primary source / grain |
|---|---|---|
| `RFM Customers` | Count of customers represented in the RFM extract. | `rfm.customer_unique_id`. |
| `Average RFM Score` | Average of the composite RFM score. | `rfm.RFM_score`. |
| `High Value Customer Rate` | High-value RFM customers divided by all RFM customers. | Segment count / RFM customer count. |
| `Average Recency` | Average number of days since the customer’s last eligible purchase at the observation cutoff. | `rfm.recency_days`. |
| `Average Frequency` | Average number of eligible orders per customer. | `rfm.frequency`. |
| `Average Monetary Value` | Average customer monetary value in BRL. | `rfm.monetary`. |

The current RFM extract uses component scores from 1 through 4:

- `R_score`: higher means more recent purchase behavior.
- `F_score`: higher means more frequent purchase behavior.
- `M_score`: higher means greater monetary value.
- `RFM_score`: `R_score + F_score + M_score`, ranging from 3 to 12.

The report uses these descriptive segments:

- `high_value`
- `regular`
- `developing`
- `needs_attention`

The RFM output is descriptive segmentation, not a prediction of future purchases.

### Cohort KPIs

| KPI | Definition | Primary source / grain |
|---|---|---|
| `Total Cohorts` | Count of distinct cohort months in the current context. | `cohort_retention.cohort_month`. |
| `Cohort Size` | Number of customers in a cohort at month 0. | `cohort_retention.cohort_size`. |
| `Average Cohort Size` | Average cohort size across selected cohorts. | Average `cohort_size`. |
| `Retained Customers` | Number of customers from a cohort active in the selected month number. | `cohort_retention.retained_customers`. |
| `Retention Rate` | Retained customers divided by cohort size, expressed as a percentage. | `retained_customers / cohort_size * 100`. |
| `Unique Retained Customers` | Distinct customers counted as retained in the current cohort/month context. | Retained customer population. |
| `Unique Unretained Customers` | Unique cohort customers not counted as retained in the selected context. | Cohort size minus retained population, subject to filter context. |
| `Unique Customers` | Distinct customer count used as the cohort comparison population. | Person-level customer identity. |

The cohort month is the customer’s first eligible delivered purchase month. The dataset is repeat-customer-prioritized, so cohort results are not representative of the full Olist customer population.

### CLV transaction KPIs

| KPI | Definition | Primary source / grain |
|---|---|---|
| `Total CLV Transactions` | Count of transaction rows in the CLV transaction extract. | `clv_transactions`; transaction grain. |
| `CLV Customers` | Distinct customers represented in the CLV transaction extract. | `clv_transactions.customer_unique_id`. |
| `Total Transaction Value` | Sum of transaction monetary values. | `clv_transactions.monetary_value`. |
| `Average Transaction Value` | Average monetary value per transaction row. | `SUM(monetary_value) / COUNT(transaction rows)`. |
| `Average Customer Transaction Value` | Average transaction value at the customer-analysis view used by the scatter plot and card. | Customer transaction value aggregated over the selected customer population. |

The CLV page is an input-analysis page. `clv_transactions` contains realized transaction values and does not represent a fitted probabilistic or predictive CLV model.

## 5. Page-by-page report documentation

## Page 1: Executive overview

### Purpose

The landing page summarizes the headline business state: customers, orders, deliveries, revenue, reviews, RFM, and category performance.

### Filters

- `Purchase Month`: filters the period using `order_fact.purchase_month`.
- `Order Status`: filters by `order_fact.order_status`.

### KPI cards

- `Unique Customers`: distinct people in the current context.
- `Average Review Score`: average review score on the 1–5 scale.
- `Total Orders`: current order count.
- `Delivered Orders`: delivered-order count.
- `Average RFM Score`: average composite RFM score.
- `Average Delivery Days`: average purchase-to-delivery duration.
- `Item Plus Freight`: total item revenue plus freight.
- `Average Order Value`: average item-plus-freight amount per order.

### Plots

1. **Monthly Revenue Trend** — line chart with purchase month on the x-axis and `Item Plus Freight` on the y-axis. It shows how item-plus-freight value changes over time. Month and status slicers change the visible series.
2. **Top 10 Categories by Revenue** — clustered bar chart with English product category on the category axis and `Category Revenue` on the value axis. It ranks the ten highest-revenue categories in the current filter context.

## Page 2: Sales analysis

### Purpose

The sales page focuses on order volume, revenue composition, payments, order status, and monthly order movement.

### Filters

- `Purchase Month`: filters order periods.
- `Order Status`: filters order status.

### KPI cards

- `Total Orders`
- `Total Revenue`
- `Item Revenue`
- `Freight Collected`
- `Payment Total`
- `Average Order Value`
- `Payment Difference`
- `Delivered Order Rate`

### Plots

1. **Monthly Order Count** — line chart with month on the x-axis and `Total Orders` on the y-axis. It shows order-volume trend over time.
2. **Revenue by Order Status** — clustered column chart with order status on the x-axis and `Total Revenue` on the y-axis. It compares item-plus-freight revenue across statuses.

The page is useful for checking whether item revenue, freight, and payments reconcile and for comparing delivered versus other order statuses where those statuses exist in the model.

## Page 3: Customer analysis

### Purpose

The customer page examines customer growth, geographic distribution, repeat behavior, and new-versus-repeat customer composition.

### Filters

- `Purchase Month`
- `Order Status`

### KPI cards

- `Unique Customers`
- `Repeat Customers`
- `Repeat Customer Rate`
- `Average Orders Per Customer`

### Plots

1. **Top 10 Customer States** — clustered bar chart with customer state on the category axis and `Unique Customers` on the value axis. It ranks the states containing the most distinct people.
2. **Customer Growth by Month** — line chart with purchase month and `Unique Customers`. It shows monthly customer activity/growth under the current filter context.
3. **New vs Repeat Customers** — clustered column chart using the date hierarchy of purchase month and the `New Customers` and `Repeat Customers` measures. It compares customer acquisition with repeat activity across the selected time hierarchy.

## Page 4: Product and category analysis

### Purpose

The product page shows catalog size, item volume, product pricing, freight cost, and category contribution.

### Filters

- `Seller State`
- `Purchase Month`

### KPI cards

- `Product Count`
- `Category Count`
- `Total Items Sold`
- `Average Item Price`
- `Average Freight Per Item`

### Plots

1. **Top 10 Items Sold by Category** — clustered bar chart with translated product category and `Category Item Count`. It ranks categories by number of sold item rows.
2. **Category Revenue Contribution** — treemap with category as the hierarchy and `Category Revenue` as the area/value. Larger rectangles represent greater category revenue contribution.
3. **Top 10 Average Freight Cost by Category** — clustered bar chart with category and `Average Freight Per Item`. It compares average logistics cost by category.
4. **Product Price versus Revenue** — product-level scatter chart. It uses product identity/category, total items sold, average item price, and item revenue to show how pricing and sales volume relate to revenue.

## Page 5: Seller analysis

### Purpose

The seller page ranks sellers by sales and freight, shows seller count and totals, and compares seller revenue with item volume.

### Filters

- `Purchase Month`
- `Seller State`

### KPI cards

- `Seller Count`
- `Seller Revenue`
- `Seller Items Sold`
- `Average Seller Freight`
- `Average Seller Order Value`

### Plots

1. **Top 10 Sellers by Revenue** — clustered bar chart with seller ID and `Seller Revenue`. It ranks sellers by item-price revenue.
2. **Top 10 Seller Freight Cost** — clustered bar chart with seller ID and `Seller Freight`. It ranks sellers by freight value.
3. **Top 10 Top Sellers by Items Sold** — clustered bar chart with seller ID and `Seller Items Sold`. It ranks sellers by item-row count.
4. **Seller Revenue versus Items Sold** — scatter chart with seller ID as the point category, seller state as the legend, seller items sold on the size/value role, seller freight and seller revenue as additional measures. It helps distinguish high-volume sellers from high-value sellers and shows state grouping.

The ranking visuals use Top 10 filtering in the report definition. Seller-state selection and purchase-month selection affect all relevant visuals.

## Page 6: Delivery analysis

### Purpose

The delivery page examines delivery speed, range, distribution, geographic differences, freight relationships, and on-time performance.

### Filters

- `Purchase Month`
- `Order Status` through the report’s order-status slicer.

### KPI cards

- `Delivered Orders`
- `Average Delivery Days`
- `Minimum Delivery Days`
- `Maximum Delivery Days`
- `On-Time Delivery Rate`

### Plots

1. **Average Delivery Days by Month** — line chart with delivery purchase month on the x-axis and average delivery days on the y-axis. It shows changes in delivery speed over time.
2. **Top 10 Average Delivery Days by Customer State** — clustered bar chart with customer state and average delivery days. It identifies states with the longest average delivery duration.
3. **Distribution of Delivery Days** — clustered column chart using binned delivery-day values and order count. It shows whether deliveries cluster around short, medium, or long durations.
4. **Freight Value vs Delivery Days** — scatter chart with freight collected on the x-axis, delivery days on the y-axis, and customer state as the legend. It explores whether higher freight is associated with longer or shorter delivery durations.

## Page 7: RFM analysis

### Purpose

The RFM page segments customers by recency, frequency, and monetary value and makes the segment distribution and customer-level relationships visible.

### Filters

- `RFM Score`
- `RFM Segment`

### KPI cards

- `RFM Customers`
- `Average RFM Score`
- `High Value Customer Rate`
- `Average Recency`
- `Average Frequency`
- `Average Monetary Value`

### Plots

1. **Customers by RFM Segment** — donut chart with RFM segment as the category and `RFM Customers` as the value. It shows the customer count mix across high-value, regular, developing, and needs-attention segments.
2. **Average Monetary Value by Segment** — clustered bar chart with RFM segment and average monetary value. It compares typical customer value across segments.
3. **Customer Frequency vs Monetary Value** — scatter chart with frequency on the x-axis, monetary value on the y-axis, customer identity as the point category, RFM score as point size, and segment as the legend. It identifies high-frequency/high-value and low-frequency/low-value populations.
4. **Customer Recency vs Monetary Value** — scatter chart with recency days on the x-axis, monetary value on the y-axis, customer identity as the point category, RFM score as point size, and segment as the legend. It shows whether high-value customers are recent or lapsed.

The RFM page is descriptive. It does not forecast future customer behavior.

## Page 8: Cohort retention

### Purpose

The cohort page measures customer retention after the first eligible purchase month.

### Filters

- `Cohort Month`
- `Month number`

### KPI cards

- `Unique Customers`
- `Total Cohorts`
- `Average Cohort Size`
- `Retention Rate`
- `Unique Retained Customers`

### Plots

1. **Cohort size by cohort month** — clustered column chart with cohort month and cohort size. It shows how many customers entered each cohort.
2. **Retention Rate by Month Number** — line chart with month number on the x-axis and retention rate. It shows the retention curve after the initial cohort month.
3. **Cohort size vs retention rate** — scatter chart with cohort size on the x-axis, retention rate on the y-axis, retained customers and cohort size in the value/size roles, and cohort month as the legend. It compares cohort scale with retention performance.
4. **Distribution of Unique Customers** — pie chart comparing unique retained and unique unretained customers. It provides a high-level retained-versus-unretained split under the selected cohort context.

Because the underlying dataset prioritizes repeat customers, retention results should be treated as analysis of this selected subset rather than a population estimate for all Olist customers.

## Page 9: CLV transactions

### Purpose

The CLV page explores realized transaction values and transaction frequency as inputs for future CLV work. It does not display predictive CLV.

### Filters

- `Transaction Date`
- `monetary Value`

### KPI cards

- `CLV Customers`
- `Average Customer Transaction Value`
- `Total Transaction Value`
- `Average Transaction Value`
- `Total CLV Transactions`

### Plots

1. **Customer Transaction Count vs Value** — scatter chart with transaction count on the x-axis and total transaction value on the y-axis. Point size uses average customer transaction value, and year is used as the legend. It highlights customers with many transactions, high total value, or both.
2. **Top 10 Customers by Transaction Value** — clustered bar chart ranking customers by total transaction value. The report definition applies a Top 10 filter.
3. **Distribution of Transaction Values** — clustered column chart using monetary-value bins and transaction count. It shows the shape of the transaction-value distribution.
4. **Transaction Value Over Time** — line chart using the transaction-date hierarchy and total transaction value. It shows how realized transaction value changes over time.

The report uses the transaction extract as a descriptive input table. It does not claim a probability model, expected future value, or predictive customer lifetime value.

## 6. Slicer behavior and filter context

Slicers are interactive filters. Their effect is applied to visuals on the same report page and may propagate through the model relationships.

Common slicers:

- **Purchase Month**: filters `order_fact.purchase_month`.
- **Order Status**: filters `order_fact.order_status`.
- **Seller State**: filters `sellers.seller_state`.
- **RFM Score**: filters `rfm.RFM_score`.
- **RFM Segment**: filters `rfm.segment`.
- **Cohort Month**: filters `cohort_retention.cohort_month`.
- **Month number**: filters `cohort_retention.month_number`.
- **Transaction Date**: filters `clv_transactions.transaction_date`.
- **monetary Value**: filters `clv_transactions.monetary_value`.

The report’s Top 10 visuals are rankings inside the current filter context. Changing a slicer can change which records appear in a Top 10 chart.

## 7. Report limitations and interpretation rules

- The report is built on a reduced, nonrandom, repeat-customer-prioritized subset.
- Revenue-related measures distinguish item revenue, freight, payments, and item-plus-freight totals. They should not be treated as interchangeable.
- Payment difference is a reconciliation diagnostic, not necessarily profit or discount.
- RFM is descriptive segmentation, not predictive scoring.
- Cohort retention is not representative of the full Olist population because of dataset selection bias.
- CLV transactions are realized transaction inputs only. Predictive CLV is not implemented.
- ZIP-prefix geolocation is a representative lookup, not precise address-level location.
- Report measures depend on the current model relationships and filter context.
- The PBIX should be refreshed only after the Python post-load pipeline succeeds and its validation output has been reviewed.

## 8. Refresh and operating workflow

The report is downstream of the data and Python workflows:

1. Preserve new raw data under `data/raw/`.
2. Run [Python/step3_prepare_data.py](../Python/step3_prepare_data.py) or the approved preparation process.
3. Review `data/quality/` artifacts.
4. Append prepared data to the MySQL `ecommerce` database.
5. Run [Python/run_post_load_pipeline.py](../Python/run_post_load_pipeline.py) with a batch ID.
6. Confirm `data/quality/post_load_pipeline_run.json` reports `success`.
7. Review the validation summary and regenerated analytics files.
8. Open [Overview.pbix](../Reports/Overview.pbix) in Power BI Desktop.
9. Use **Home → Refresh**.
10. Verify dates, order counts, customers, revenue, delivery, RFM, cohort, seller, and product visuals.
11. Save the refreshed PBIX.

The full future-batch process is documented in [future_batch_data_runbook.md](./future_batch_data_runbook.md).

## 9. How to open the report

From PowerShell, after Power BI Desktop is installed:

```powershell
cd C:\Users\mukth\OneDrive\Desktop\E-commerce
Start-Process Reports\Overview.pbix
```

The report can also be opened directly from Power BI Desktop with **File → Open**.
