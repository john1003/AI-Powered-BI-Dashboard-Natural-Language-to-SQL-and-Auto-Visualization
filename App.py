import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import ollama
import matplotlib.pyplot as plt
import re
import os
from dotenv import load_dotenv

# ---------------- LOAD ENV VARIABLES ----------------
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# ---------------- MYSQL CONNECTION ----------------
from urllib.parse import quote_plus
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

st.set_page_config(layout="wide", page_title="AI BI Dashboard")
st.title("🧠 AI SQL Generator (Local - Qwen 2.5)")

# ---------------- SCHEMA CONTEXT ----------------
schema_context = """
You are a MySQL SQL generator.

Database: ai_bi_dashboard

Tables and their EXACT columns:

orders(Order_ID, Order_Date, Ship_Date, Ship_Mode, Customer_ID, Customer_Name, Segment, Country, City, State, Region, Product_ID, Category, Sub_Category, Product_Name, Sales, Quantity, Discount, Profit)

returns(Order_ID, Returned)

people(Region, Person)

STRICT RULES:
- Only generate SELECT queries
- Use valid MySQL syntax
- Only reference columns that exist in the tables above
- When joining tables, use correct table aliases consistently
- Example: SELECT o.Region, SUM(o.Sales) FROM orders o GROUP BY o.Region
- No explanation, No markdown, No ```sql blocks
- Return plain SQL only ending with semicolon
"""

# ---------------- CLEAN SQL ----------------
def clean_sql(raw: str) -> str:
    raw = re.sub(r"```sql|```", "", raw, flags=re.IGNORECASE)
    lines = raw.strip().splitlines()
    sql_lines = []
    sql_started = False
    for line in lines:
        if line.strip().upper().startswith(("SELECT", "WITH", "INSERT", "UPDATE", "DELETE")):
            sql_started = True
        if sql_started:
            sql_lines.append(line)
    result = "\n".join(sql_lines).strip()
    return result if result else raw.strip()

# ---------------- SESSION STATE ----------------
if "queries" not in st.session_state:
    st.session_state.queries = []
# Each entry: { question, sql, df or None, error or None }

# ---------------- INPUT at top ----------------
st.subheader("🔍 Ask a Question")
question = st.text_input("Ask your business question", key="question_input")

if st.button("Generate & Run"):
    if question:
        with st.spinner("Generating SQL with Qwen 2.5..."):
            response = ollama.chat(
                model="qwen2.5-coder:7b",
                messages=[
                    {"role": "system", "content": schema_context},
                    {"role": "user", "content": f"Generate a MySQL query for: {question}"}
                ]
            )
            raw_sql = response["message"]["content"].strip()
            sql_query = clean_sql(raw_sql)

        try:
            df = pd.read_sql(text(sql_query), engine)
            st.session_state.queries.append({
                "question": question,
                "sql": sql_query,
                "df": df,
                "error": None
            })
        except Exception as e:
            st.session_state.queries.append({
                "question": question,
                "sql": sql_query,
                "df": None,
                "error": str(e)
            })

st.markdown("---")

# ---------------- DISPLAY ALL QUERIES ----------------
for i, item in enumerate(st.session_state.queries):
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.markdown(f"### Q{i+1}: {item['question']}")
        st.code(item["sql"], language="sql")

        if item["df"] is not None:
            st.subheader("Query Result")
            st.dataframe(item["df"], use_container_width=True)
        else:
            st.error(f"SQL Execution Error: {item['error']}")
            st.info("💡 Try rephrasing your question.")

    with right_col:
        if item["df"] is not None:
            df = item["df"]
            if len(df.columns) >= 2:
                col1 = df.columns[0]
                col2 = df.columns[1]
                if pd.api.types.is_numeric_dtype(df[col2]):
                    st.subheader("📊 Chart")
                    fig, ax = plt.subplots(figsize=(6, 5))
                    df.plot(kind="bar", x=col1, y=col2, ax=ax, legend=False, color="steelblue")
                    ax.set_title(item["question"])
                    ax.set_xlabel(col1)
                    ax.set_ylabel(col2)
                    plt.xticks(rotation=45, ha="right")
                    plt.tight_layout()
                    st.pyplot(fig)

    st.markdown("---")

# Clear button at bottom
if st.session_state.queries:
    if st.button("🗑️ Clear All"):
        st.session_state.queries = []
        st.rerun()
