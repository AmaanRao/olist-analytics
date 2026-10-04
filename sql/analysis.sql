-- ============================================================
-- Olist late-delivery analysis
-- Business question: do late deliveries lower review scores,
-- and which states / sellers are worst?
-- Engine: SQLite.  Run after building olist.db with load_db.py.
-- ============================================================

DROP VIEW IF EXISTS v_order_delivery;
CREATE VIEW v_order_delivery AS
SELECT
  o.order_id,
  c.customer_state,
  o.order_purchase_timestamp,
  ROUND(julianday(o.order_delivered_customer_date)
        - julianday(o.order_estimated_delivery_date), 2)          AS delay_days,
  CASE
    WHEN julianday(o.order_delivered_customer_date)
         - julianday(o.order_estimated_delivery_date) <= 0 THEN 'On time / early'
    WHEN julianday(o.order_delivered_customer_date)
         - julianday(o.order_estimated_delivery_date) <= 3 THEN 'Slightly late (1-3d)'
    WHEN julianday(o.order_delivered_customer_date)
         - julianday(o.order_estimated_delivery_date) <= 7 THEN 'Late (4-7d)'
    ELSE 'Very late (8d+)'
  END                                                             AS delivery_bucket,
  r.review_score
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN reviews   r ON r.order_id    = o.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL;

-- 1. Headline: review score by delivery timeliness
SELECT delivery_bucket, COUNT(*) AS orders, ROUND(AVG(review_score), 2) AS avg_score
FROM v_order_delivery
GROUP BY delivery_bucket
ORDER BY avg_score DESC;

-- 2. Worst states by on-time delivery rate
SELECT
  customer_state,
  COUNT(*) AS orders,
  ROUND(100.0 * AVG(CASE WHEN delay_days <= 0 THEN 1 ELSE 0 END), 1) AS on_time_rate,
  ROUND(AVG(review_score), 2) AS avg_score
FROM v_order_delivery
GROUP BY customer_state
HAVING COUNT(*) >= 50
ORDER BY on_time_rate ASC
LIMIT 10;

-- 3. Worst sellers by late-delivery rate (deduped to one row per seller-order)
WITH seller_orders AS (
  SELECT DISTINCT oi.seller_id, v.order_id, v.delay_days, v.review_score
  FROM order_items oi
  JOIN v_order_delivery v ON v.order_id = oi.order_id
)
SELECT
  seller_id,
  COUNT(*) AS orders,
  ROUND(100.0 * AVG(CASE WHEN delay_days > 0 THEN 1 ELSE 0 END), 1) AS late_rate,
  ROUND(AVG(review_score), 2) AS avg_score
FROM seller_orders
GROUP BY seller_id
HAVING COUNT(*) >= 50
ORDER BY late_rate DESC
LIMIT 10;
