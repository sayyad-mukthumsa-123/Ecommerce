-- Step 6: Post-load QA, EDA, and analytical SQL
-- Database: ecommerce
-- Eligible population: delivered orders
-- Customer identity: customer_unique_id identifies a person across orders.
-- All monetary values are in Brazilian reais (BRL).

USE ecommerce;

-- Query 1: Count rows in the main transactional tables after loading.
SELECT 'orders' AS table_name, COUNT(*) AS row_count FROM orders
UNION ALL
SELECT 'customers', COUNT(*) FROM customers
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'payments', COUNT(*) FROM payments
UNION ALL
SELECT 'reviews', COUNT(*) FROM reviews;

-- Query 2: Check order status values to confirm the eligible population.
SELECT order_status, COUNT(*) AS order_count
FROM orders
GROUP BY order_status
ORDER BY order_count DESC;

-- Query 3: Check missing values in important order columns.
SELECT
    SUM(order_id IS NULL) AS missing_order_id,
    SUM(customer_id IS NULL) AS missing_customer_id,
    SUM(order_status IS NULL) AS missing_order_status,
    SUM(order_purchase_timestamp IS NULL) AS missing_purchase_timestamp
FROM orders;

-- Query 4: Check that every order is linked to a customer row.
SELECT COUNT(*) AS orphan_order_customer_rows
FROM orders o
LEFT JOIN customers c ON c.customer_id = o.customer_id
WHERE c.customer_id IS NULL;

-- Query 5: Check that every order item references a valid order, product, and seller.
SELECT
    SUM(o.order_id IS NULL) AS orphan_orders,
    SUM(p.product_id IS NULL) AS orphan_products,
    SUM(s.seller_id IS NULL) AS orphan_sellers
FROM order_items oi
LEFT JOIN orders o ON o.order_id = oi.order_id
LEFT JOIN products p ON p.product_id = oi.product_id
LEFT JOIN sellers s ON s.seller_id = oi.seller_id;

-- Query 6: Calculate item revenue and freight separately for each delivered order.
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

-- Query 7: Calculate monthly delivered-order revenue and order volume.
SELECT
    DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS purchase_month,
    COUNT(DISTINCT o.order_id) AS order_count,
    COUNT(DISTINCT c.customer_unique_id) AS unique_customers,
    ROUND(SUM(oi.price), 2) AS item_revenue,
    ROUND(SUM(oi.freight_value), 2) AS freight_collected
FROM orders o
INNER JOIN customers c ON c.customer_id = o.customer_id
INNER JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')
ORDER BY purchase_month;

-- Query 8: Find the top product categories by delivered item revenue.
SELECT
    COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category_name,
    COUNT(*) AS item_count,
    ROUND(SUM(oi.price), 2) AS item_revenue
FROM order_items oi
INNER JOIN orders o ON o.order_id = oi.order_id
INNER JOIN products p ON p.product_id = oi.product_id
LEFT JOIN category_translation t
    ON t.product_category_name = p.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY COALESCE(t.product_category_name_english, p.product_category_name, 'unknown')
ORDER BY item_revenue DESC
LIMIT 10;

-- Query 9: Build a customer-level RFM summary.
SELECT
    c.customer_unique_id,
    DATEDIFF('2018-08-28', MAX(o.order_purchase_timestamp)) AS recency_days,
    COUNT(DISTINCT o.order_id) AS frequency_orders,
    ROUND(SUM(oi.price + oi.freight_value), 2) AS monetary_value
FROM orders o
INNER JOIN customers c ON c.customer_id = o.customer_id
INNER JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_unique_id
ORDER BY monetary_value DESC;

-- Query 10: Identify repeat customers using the person-level customer key.
SELECT COUNT(*) AS repeat_customer_count
FROM (
    SELECT c.customer_unique_id
    FROM orders o
    INNER JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
    HAVING COUNT(DISTINCT o.order_id) > 1
) repeat_customers;

-- Query 11: Calculate monthly cohort retention.
WITH customer_orders AS (
    SELECT DISTINCT
        c.customer_unique_id,
        DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m-01') AS purchase_month
    FROM orders o
    INNER JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
), first_purchase AS (
    SELECT customer_unique_id, MIN(purchase_month) AS cohort_month
    FROM customer_orders
    GROUP BY customer_unique_id
)
SELECT
    f.cohort_month,
    TIMESTAMPDIFF(MONTH, f.cohort_month, co.purchase_month) AS month_number,
    COUNT(DISTINCT co.customer_unique_id) AS retained_customers
FROM first_purchase f
INNER JOIN customer_orders co ON co.customer_unique_id = f.customer_unique_id
GROUP BY f.cohort_month, TIMESTAMPDIFF(MONTH, f.cohort_month, co.purchase_month)
ORDER BY f.cohort_month, month_number;

-- Query 12: Summarize delivery time for delivered orders with available timestamps.
SELECT
    ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)), 2) AS average_delivery_days,
    MIN(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)) AS minimum_delivery_days,
    MAX(DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)) AS maximum_delivery_days
FROM orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL;
