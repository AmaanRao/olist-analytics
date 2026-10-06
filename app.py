"""Olist Delivery Analytics - Streamlit app: dashboard + AI question box."""
import os, sqlite3, textwrap, time, warnings, requests
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
warnings.filterwarnings("ignore")

load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")
MODEL = "gemini-flash-lite-latest"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
DB = os.path.join(os.path.dirname(__file__), "olist.db")

st.set_page_config(page_title="Olist Delivery Analytics", page_icon="📦", layout="wide")

# ---------- database ----------
@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.executescript("""
    DROP VIEW IF EXISTS v_order_delivery;
    CREATE VIEW v_order_delivery AS
    SELECT o.order_id, c.customer_state,
      ROUND(julianday(o.order_delivered_customer_date)
            - julianday(o.order_estimated_delivery_date),2) AS delay_days,
      CASE
        WHEN julianday(o.order_delivered_customer_date)-julianday(o.order_estimated_delivery_date)<=0 THEN 'On time / early'
        WHEN julianday(o.order_delivered_customer_date)-julianday(o.order_estimated_delivery_date)<=3 THEN 'Slightly late (1-3d)'
        WHEN julianday(o.order_delivered_customer_date)-julianday(o.order_estimated_delivery_date)<=7 THEN 'Late (4-7d)'
        ELSE 'Very late (8d+)' END AS delivery_bucket,
      r.review_score
    FROM orders o
    JOIN customers c ON c.customer_id=o.customer_id
    JOIN reviews   r ON r.order_id=o.order_id
    WHERE o.order_status='delivered' AND o.order_delivered_customer_date IS NOT NULL;
    """)
    return conn

conn = get_conn()

@st.cache_data
def q(sql):
    return pd.read_sql(sql, conn)

# ---------- header ----------
st.title("📦 Olist: How Late Deliveries Hurt Reviews")
st.caption("Analysis of ~96,000 delivered orders · SQLite + SQL · with an AI query assistant")

# ---------- KPIs ----------
k = q("""SELECT COUNT(*) AS orders,
         ROUND(100.0*AVG(CASE WHEN delay_days<=0 THEN 1 ELSE 0 END),1) AS on_time,
         ROUND(AVG(review_score),2) AS avg_score FROM v_order_delivery""").iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("Delivered orders", f"{int(k.orders):,}")
c2.metric("On-time rate", f"{k.on_time}%")
c3.metric("Avg review score", f"{k.avg_score} ★")

st.divider()

# ---------- charts ----------
left, right = st.columns(2)

with left:
    st.subheader("Review score by delivery timeliness")
    d1 = q("""SELECT delivery_bucket, ROUND(AVG(review_score),2) AS avg_score
              FROM v_order_delivery GROUP BY delivery_bucket ORDER BY avg_score DESC""")
    fig1 = px.bar(d1, x="delivery_bucket", y="avg_score", text="avg_score",
                  color="avg_score", color_continuous_scale="RdYlGn", range_y=[0, 5])
    fig1.update_layout(showlegend=False, coloraxis_showscale=False,
                       xaxis_title="", yaxis_title="Avg score")
    st.plotly_chart(fig1, use_container_width=True)

with right:
    st.subheader("Worst 10 states by on-time rate")
    d2 = q("""SELECT customer_state,
              ROUND(100.0*AVG(CASE WHEN delay_days<=0 THEN 1 ELSE 0 END),1) AS on_time_rate
              FROM v_order_delivery GROUP BY customer_state HAVING COUNT(*)>=50
              ORDER BY on_time_rate ASC LIMIT 10""")
    fig2 = px.bar(d2, x="on_time_rate", y="customer_state", orientation="h", text="on_time_rate")
    fig2.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="On-time %", yaxis_title="")
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ---------- AI query box ----------
st.subheader("🤖 Ask the data a question (AI → SQL)")
st.write("Type a question in plain English. Gemini writes the SQL, it runs, and the answer appears below.")

SCHEMA = textwrap.dedent("""
  SQLite view: v_order_delivery(order_id, customer_state, delay_days, review_score)
  delay_days positive = late; delivered orders only; review_score 1..5.
  Base tables: orders, customers(customer_state),
  order_items(order_id, product_id, seller_id, price, freight_value),
  products(product_id, product_category_name), sellers, reviews.
""")

def ask_gemini(question):
    prompt = (f"You are a SQL analyst. Using ONLY this SQLite schema:\n{SCHEMA}\n"
                            f"Write ONE read-only SELECT that answers: {question}. "
              f"When ranking or grouping, also SELECT the numeric measure column so it can be charted.\n"
              "Return ONLY the SQL - no explanation, no markdown fences.")
    last = ""
    for attempt in range(4):
        try:
            r = requests.post(URL, params={"key": API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        except requests.exceptions.RequestException as e:
            last = f"network/timeout: {e}"; time.sleep(2); continue
        if r.status_code in (503, 429):
            last = f"status {r.status_code}"; time.sleep(3); continue
        r.raise_for_status()
        txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return txt.strip().strip("`").replace("sql\n", "", 1).strip()
    raise RuntimeError(f"Gemini didn't respond after 4 tries ({last}). Please try again.")

question = st.text_input("Your question", "which 5 sellers ship late most often?")
if st.button("Ask", type="primary"):
    if not API_KEY:
        st.error("No GOOGLE_API_KEY found in .env")
    else:
        with st.spinner("Gemini is writing SQL..."):
            try:
                sql = ask_gemini(question)
                st.markdown("**Generated SQL:**")
                st.code(sql, language="sql")
                if sql.lower().lstrip().startswith(("select", "with")):
                    df = pd.read_sql(sql, conn)
                    st.markdown("**Result:**")
                    st.dataframe(df, use_container_width=True)
                    if df.shape[1] == 2 and pd.api.types.is_numeric_dtype(df.iloc[:, 1]):
                        st.bar_chart(df.set_index(df.columns[0]))
                else:
                    st.warning("That wasn't a read-only SELECT, so it wasn't run.")
            except Exception as e:
                st.error(f"Something went wrong: {e}")

st.caption("Demo note: the AI writes SQL; it runs read-only and always shows the query for review.")