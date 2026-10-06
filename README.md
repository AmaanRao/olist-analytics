# Olist: How Late Deliveries Hurt Reviews

A data-analyst portfolio project analysing **96,478 delivered orders** from the public
Olist Brazilian e-commerce dataset, to answer a real business question:
**do late deliveries lower customer review scores — and where should the business act?**

**[View the interactive Tableau dashboard »](https://public.tableau.com/app/profile/amaan.rao1607/viz/OlistDeliveryAnalytics/OlistHowDeliveriesHurtReviews_)**

## Key findings
- **Late delivery is the biggest driver of bad reviews.** Average review score falls
  from **4.29** (on time) to **1.73** (8+ days late).
- **The problem is regional** — the worst states (Alagoas 77% on-time) are in the
  remote northeast, far from the São Paulo logistics hub.
- **A small group of sellers** ships late on up to **29%** of orders — the clearest
  operational lever.

## Tech stack
SQLite · SQL (views, CTEs, conditional aggregation) · Python (pandas) · Tableau Public

## Pipeline
Raw CSVs → SQLite database → SQL analysis → exported CSVs → Tableau dashboard.

## Repo structure
- `scripts/load_db.py` — loads the Olist CSVs into a SQLite database
- `sql/analysis.sql` — the full analysis (view + queries)
- `docs/study_notes.md` — notes on the approach and SQL concepts
- (data is not committed — see below)

## How to run
1. Download the *Brazilian E-Commerce Public Dataset by Olist* from Kaggle and put the
   CSVs in `data/`.
2. `pip install pandas` then `python3 scripts/load_db.py` to build `olist.db`.
3. `sqlite3 olist.db < sql/analysis.sql` to run the analysis.

## AI layer (natural language to SQL)
scripts/ai_query.py sends a plain-English question plus the database schema to Google
Gemini, which writes a read-only SQL query; the script runs it and prints both the SQL
and the result. Example: python3 scripts/ai_query.py "which 5 states have the worst on-time delivery rate?"

## Interactive web app (Streamlit)
app.py is a Streamlit web app combining the charts and a live AI question box on one page.
Run it with: streamlit run app.py