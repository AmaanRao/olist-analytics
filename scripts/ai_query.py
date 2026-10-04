"""Natural-language -> SQL over olist.db, using Google Gemini via its REST API."""
import os, sys, sqlite3, textwrap, time, warnings, requests
from dotenv import load_dotenv
warnings.filterwarnings("ignore")  # hide the harmless LibreSSL notice

load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    sys.exit("No GOOGLE_API_KEY found - put it in a .env file.")

MODEL = "gemini-flash-latest"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
DB = os.path.join(os.path.dirname(__file__), "..", "olist.db")

SCHEMA = textwrap.dedent("""
  SQLite view available: v_order_delivery(order_id, customer_state, delay_days, review_score)
  where delay_days = delivered minus estimated date (positive = late), delivered orders only,
  review_score is 1..5. Base tables: orders, customers(customer_state),
  order_items(order_id, product_id, seller_id, price, freight_value),
  products(product_id, product_category_name), sellers, reviews.
""")

def make_view(conn):
    conn.executescript("""
    DROP VIEW IF EXISTS v_order_delivery;
    CREATE VIEW v_order_delivery AS
    SELECT o.order_id, c.customer_state,
      ROUND(julianday(o.order_delivered_customer_date)
            - julianday(o.order_estimated_delivery_date),2) AS delay_days,
      r.review_score
    FROM orders o
    JOIN customers c ON c.customer_id=o.customer_id
    JOIN reviews   r ON r.order_id=o.order_id
    WHERE o.order_status='delivered' AND o.order_delivered_customer_date IS NOT NULL;
    """)

def ask_gemini(question):
    prompt = (f"You are a SQL analyst. Using ONLY this SQLite schema:\n{SCHEMA}\n"
              f"Write ONE read-only SELECT that answers: {question}\n"
              "Return ONLY the SQL - no explanation, no markdown fences.")
    for attempt in range(3):  # retry on transient 503s
        r = requests.post(URL, params={"key": API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        if r.status_code in (503, 429):
            time.sleep(2); continue
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip().strip("`").replace("sql\n", "", 1).strip()
    sys.exit("Gemini is busy (503) after 3 tries - please run it again.")

def run(question):
    sql = ask_gemini(question)
    print("\nGenerated SQL\n-------------\n" + sql + "\n")
    if not sql.lower().lstrip().startswith(("select", "with")):
        print("Refused: not a read-only SELECT."); return
    conn = sqlite3.connect(DB); make_view(conn)
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(50)
    except Exception as e:
        print("SQL error:", e); return
    print("Result\n------")
    print(" | ".join(cols))
    for row in rows:
        print(" | ".join(str(x) for x in row))

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or input("Ask about the Olist data: ")
    run(q)