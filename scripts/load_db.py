"""Load the Olist CSV files into a single SQLite database (olist.db)."""
import sqlite3
import pandas as pd
import pathlib

# Paths: BASE is the project folder (one level up from this scripts/ file)
BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / "data"
DB = BASE / "olist.db"

# Map each CSV file -> the table name we want inside the database
TABLES = {
    "olist_customers_dataset.csv":     "customers",
    "olist_orders_dataset.csv":        "orders",
    "olist_order_items_dataset.csv":   "order_items",
    "olist_products_dataset.csv":      "products",
    "olist_sellers_dataset.csv":       "sellers",
    "olist_order_reviews_dataset.csv": "reviews",
    "olist_order_payments_dataset.csv":"payments",
}

def main():
    if DB.exists():
        DB.unlink()                       # delete old db so each run starts fresh
    conn = sqlite3.connect(DB)            # opens (and creates) olist.db

    for filename, table in TABLES.items():
        df = pd.read_csv(DATA / filename)                          # CSV -> table in memory
        df.to_sql(table, conn, if_exists="replace", index=False)  # write it into the database
        print(f"loaded {table:12s} {len(df):>7,} rows")

    # Indexes make the joins in our analysis much faster
    for stmt in [
        "CREATE INDEX idx_orders_customer ON orders(customer_id)",
        "CREATE INDEX idx_items_order   ON order_items(order_id)",
        "CREATE INDEX idx_items_seller  ON order_items(seller_id)",
        "CREATE INDEX idx_reviews_order ON reviews(order_id)",
    ]:
        conn.execute(stmt)

    conn.commit()    # save the changes
    conn.close()     # close the connection cleanly
    print(f"\nDatabase written to {DB}")

if __name__ == "__main__":
    main()