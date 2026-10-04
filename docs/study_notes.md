# Olist Late-Delivery Analysis — Study Notes

## The business question
Do late deliveries lower customer review scores, and which states and sellers are worst?
Reviews drive repeat purchase and search ranking, so this is really a revenue question.

## Pipeline overview (say this in interviews)
Raw CSVs  ->  SQLite database  ->  SQL analysis  ->  exported CSV  ->  Tableau dashboard.
A small ETL pipeline: **E**xtract from CSVs, **L**oad into SQLite, **T**ransform with SQL, visualize.

Files:
- `scripts/load_db.py`  : loads the 7 CSVs into `olist.db`
- `sql/analysis.sql`    : the view + 3 analytical queries
- `data/olist_analysis.csv` : query output exported for Tableau

---

## Part A — load_db.py (CSV -> database)
- `pd.read_csv()` reads each CSV into a DataFrame (a table in memory).
- `df.to_sql(table, conn, if_exists="replace")` writes it into the SQLite database.
- `CREATE INDEX` on join keys (customer_id, order_id, seller_id) makes joins fast.
- `conn.commit()` saves; `conn.close()` releases the file.
One-liner: "A Python/pandas script loads the CSVs into SQLite and indexes the join keys."

---

## Part B — the SQL

### The view (foundation)
`CREATE VIEW v_order_delivery` = one reusable, pre-joined table:
- JOIN orders -> customers (get state) and orders -> reviews (get score).
- `julianday(delivered) - julianday(estimated)` = delay_days (positive = late).
- `CASE WHEN ... END` buckets delay_days into On time / Slightly late / Late / Very late.
- `WHERE order_status='delivered'` keeps only orders we can judge.

### Query 1 - headline (review score by lateness)
GROUP BY delivery_bucket, then AVG(review_score) per bucket.
Finding: 4.29 (on time) -> 3.77 -> 2.32 -> 1.73 (very late).

### Query 2 - worst states
Conditional aggregation: AVG(CASE WHEN delay_days<=0 THEN 1 ELSE 0 END)*100 = on-time %.
HAVING COUNT(*)>=50 drops tiny states.
Finding: Alagoas (AL) worst at 76.6%; northeastern states dominate.

### Query 3 - worst sellers
CTE (WITH ... AS) + SELECT DISTINCT to dedupe multi-item orders before aggregating.
Finding: worst sellers ship late 25-29% of the time.

---

## SQL concepts I can now claim
JOIN (combine tables on keys) | WHERE vs HAVING (rows before vs groups after) |
GROUP BY + AVG/COUNT (aggregation) | CASE WHEN (conditional logic) |
conditional aggregation (rates in one expression) | CTE / WITH | DISTINCT (dedupe) |
views (reusable saved queries) | date math with julianday.

## WHERE vs HAVING (the classic gotcha)
WHERE filters individual rows BEFORE grouping.
HAVING filters whole groups AFTER grouping (used with COUNT/AVG/etc).

## Findings in business language
1. Late delivery is the biggest driver of bad reviews (4.3 -> 1.7 stars).
2. The problem is regional - remote northeastern states are worst (far from the SP hub).
3. A small set of sellers causes an outsized share of lateness - a clear place to intervene.
