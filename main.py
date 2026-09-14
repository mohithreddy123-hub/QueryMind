import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from decimal import Decimal

from app.retriever import retrieve_schema, format_schema_for_prompt
from app.sql_generator import generate_sql
from app.sql_validator import validate_sql
from app.sql_executor import execute_sql
from app.responder import generate_response
from config.settings import TOP_K, MAX_RESULT_ROWS

st.set_page_config(
    page_title="QueryMind",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.stApp {
    background-color: #0d0e12 !important;
    color: #ececf1 !important;
}

section.main > div {
    max-width: 800px !important;
    padding-top: 1rem !important;
    padding-bottom: 5rem !important;
    margin: 0 auto !important;
}

[data-testid="stSidebar"] {
    background-color: #121318 !important;
    border-right: 1px solid #1f2129 !important;
}
[data-testid="stSidebar"] * {
    color: #b4b6c3 !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
    color: #e2e4ea !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
}

div[data-testid="stSidebarCollapseButton"] button {
    color: #b4b6c3 !important;
}

[data-testid="stChatMessage"] {
    background-color: transparent !important;
    border: none !important;
    padding: 1.25rem 0.5rem !important;
    margin-bottom: 0.25rem !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: transparent !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: transparent !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
}

[data-testid="stChatInput"] {
    max-width: 800px !important;
    margin: 0 auto !important;
}
[data-testid="stChatInput"] textarea {
    background-color: #17181f !important;
    border: 1px solid #292b36 !important;
    border-radius: 24px !important;
    color: #f1f2f6 !important;
    font-size: 15px !important;
    line-height: 1.5 !important;
    padding: 12px 18px !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #585bf6 !important;
    box-shadow: 0 0 0 2px rgba(88, 91, 246, 0.25) !important;
}
[data-testid="stChatInput"] button {
    color: #8c8fa1 !important;
}
[data-testid="stChatInput"] button:hover {
    color: #585bf6 !important;
}

[data-testid="stExpander"] {
    background: #12131a !important;
    border: 1px solid #21232e !important;
    border-radius: 10px !important;
    margin-top: 10px !important;
}
[data-testid="stExpander"] summary {
    font-size: 12px !important;
    color: #8d91a5 !important;
    font-weight: 500 !important;
    padding: 6px 12px !important;
}
[data-testid="stExpander"] summary:hover {
    color: #c7cad8 !important;
}

pre, code {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: #101117 !important;
    border-radius: 8px !important;
    border: 1px solid #222430 !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid #222430 !important;
    border-radius: 8px !important;
    background: #101117 !important;
}

.stButton > button {
    background-color: #171821 !important;
    border: 1px solid #262837 !important;
    color: #c9cddb !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 12px !important;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    background-color: #202230 !important;
    border-color: #3f435c !important;
    color: #ffffff !important;
}

.tag-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500;
    margin-right: 6px;
    margin-bottom: 4px;
    background: #1a1c26;
    border: 1px solid #2b2e3e;
    color: #9da1b6;
}
</style>
""", unsafe_allow_html=True)


def serialize_rows(rows: list[dict]) -> list[dict]:
    clean = []
    for row in rows:
        clean.append({
            k: float(v) if isinstance(v, Decimal) else v
            for k, v in row.items()
        })
    return clean


if "history" not in st.session_state:
    st.session_state.history = []

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


with st.sidebar:
    st.markdown("""
    <div style="padding: 10px 0 16px 0; display: flex; align-items: center; gap: 10px;">
        <div style="
            width: 32px; height: 32px; border-radius: 8px;
            background: #585bf6; display: flex; align-items: center;
            justify-content: center; font-size: 16px;
        ">✨</div>
        <div>
            <div style="font-weight: 700; font-size: 15px; color: #f1f2f6;">QueryMind</div>
            <div style="font-size: 11px; color: #767a8f;">Text-to-SQL Assistant</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("＋  New conversation", use_container_width=True):
        st.session_state.history = []
        st.session_state.pending_query = None
        st.rerun()

    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
    st.caption("EXAMPLE QUESTIONS")

    suggested = [
        ("📈 Top Selling Products", "Which product sold the most this month?"),
        ("💰 Revenue Summary", "What is the total revenue from paid orders?"),
        ("👥 Customer Hubs", "Which city has the most customers?"),
        ("📉 Low Inventory", "Show top 5 products with the lowest stock"),
        ("⭐ Low Rated Items", "Which product has the worst average rating?"),
    ]

    for label, prompt_text in suggested:
        if st.button(label, key=f"side_{label}", use_container_width=True):
            st.session_state.pending_query = prompt_text
            st.rerun()

    st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div style="
        background: #16171f;
        border: 1px solid #222432;
        border-radius: 10px;
        padding: 12px;
        font-size: 12px;
    ">
        <div style="font-weight: 600; color: #e2e4ea; margin-bottom: 6px;">
            🗄️ text_to_sql_db
        </div>
        <div style="color: #7b8096; line-height: 1.6;">
            • 5 Tables Connected<br>
            • 23,300 Records (Read-Only)<br>
            • ChromaDB Vector Store Active
        </div>
    </div>
    """, unsafe_allow_html=True)


if not st.session_state.history:
    st.markdown("""
    <div style="text-align: center; padding: 60px 10px 30px 10px;">
        <div style="
            display: inline-flex; width: 48px; height: 48px; border-radius: 12px;
            background: linear-gradient(135deg, #585bf6 0%, #7c3aed 100%);
            align-items: center; justify-content: center; font-size: 22px;
            margin-bottom: 16px; box-shadow: 0 8px 24px rgba(88, 91, 246, 0.35);
        ">✨</div>
        <h1 style="
            font-size: 28px; font-weight: 600; color: #f3f4f6;
            margin: 0 0 8px 0; letter-spacing: -0.5px;
        ">What would you like to know?</h1>
        <p style="
            color: #82879a; font-size: 15px; margin: 0 auto; max-width: 460px; line-height: 1.5;
        ">Ask questions about your sales, inventory, customers, or revenue in natural language.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊  Top-selling products this month", use_container_width=True):
            st.session_state.pending_query = "Which product sold the most this month?"
            st.rerun()
        if st.button("📍  Cities with most registered customers", use_container_width=True):
            st.session_state.pending_query = "Which city has the most customers?"
            st.rerun()

    with col2:
        if st.button("💳  Total revenue from successful orders", use_container_width=True):
            st.session_state.pending_query = "What is the total revenue from paid orders?"
            st.rerun()
        if st.button("📦  Products with critically low stock", use_container_width=True):
            st.session_state.pending_query = "Show top 5 products with the lowest stock"
            st.rerun()

else:
    for msg in st.session_state.history:
        with st.chat_message("user"):
            st.markdown(msg["question"])

        with st.chat_message("assistant", avatar="✨"):
            if not msg["success"]:
                st.error(msg["error"])
            else:
                st.markdown(msg["answer"])

                with st.expander("⚡ View generated SQL & database results", expanded=False):
                    if "retrieved_tables" in msg and msg["retrieved_tables"]:
                        tags_html = "".join([
                            f'<span class="tag-badge">{t} ({s:.2f})</span>'
                            for t, s in zip(msg["retrieved_tables"], msg.get("similarity_scores", []))
                        ])
                        st.markdown(f"**Retrieved Tables:** {tags_html}", unsafe_allow_html=True)

                    st.markdown("**SQL Executed:**")
                    st.code(msg["sql"], language="sql")

                    if msg.get("rows"):
                        row_info = f"**Results:** {msg['row_count']} row(s)"
                        if msg.get("truncated"):
                            row_info += f" (showing first {MAX_RESULT_ROWS})"
                        st.caption(row_info)
                        st.dataframe(msg["rows"], use_container_width=True, hide_index=True)
                    else:
                        st.caption("Query executed successfully — 0 rows returned.")


user_input = st.chat_input("Ask about your data (e.g., 'What was our total revenue last month?')...")
query_to_run = user_input or st.session_state.pending_query

if query_to_run:
    st.session_state.pending_query = None

    with st.chat_message("user"):
        st.markdown(query_to_run)

    with st.chat_message("assistant", avatar="✨"):
        with st.spinner("Analyzing database and synthesizing answer..."):
            try:
                docs = retrieve_schema(query_to_run)
                schema_text = format_schema_for_prompt(docs)
                retrieved_tables = [d["table_name"] for d in docs]
                similarity_scores = [d["similarity"] for d in docs]
            except Exception as e:
                err = f"Schema retrieval error: {e}"
                st.error(err)
                st.session_state.history.append({
                    "question": query_to_run, "success": False, "error": err
                })
                st.stop()

            gen = generate_sql(query_to_run, schema_text)
            if not gen["success"]:
                err = f"SQL generation error: {gen['error']}"
                st.error(err)
                st.session_state.history.append({
                    "question": query_to_run, "success": False, "error": err
                })
                st.stop()

            val = validate_sql(gen["sql"])
            if not val["valid"]:
                err = f"Security block: {val['reason']}"
                st.warning(err)
                st.session_state.history.append({
                    "question": query_to_run, "success": False, "error": err,
                    "sql": gen["sql"], "retrieved_tables": retrieved_tables,
                    "similarity_scores": similarity_scores
                })
                st.stop()

            exe = execute_sql(gen["sql"])
            if not exe["success"]:
                err = f"Database error: {exe['error']}"
                st.error(err)
                st.session_state.history.append({
                    "question": query_to_run, "success": False, "error": err,
                    "sql": gen["sql"], "retrieved_tables": retrieved_tables,
                    "similarity_scores": similarity_scores
                })
                st.stop()

            resp = generate_response(
                query_to_run, gen["sql"], exe["rows"], exe["row_count"], exe["truncated"]
            )

        st.markdown(resp["answer"])

        with st.expander("⚡ View generated SQL & database results", expanded=False):
            tags_html = "".join([
                f'<span class="tag-badge">{t} ({s:.2f})</span>'
                for t, s in zip(retrieved_tables, similarity_scores)
            ])
            st.markdown(f"**Retrieved Tables:** {tags_html}", unsafe_allow_html=True)
            st.markdown("**SQL Executed:**")
            st.code(gen["sql"], language="sql")

            if exe["rows"]:
                clean_rows = serialize_rows(exe["rows"])
                st.caption(f"**Results:** {exe['row_count']} row(s)")
                st.dataframe(clean_rows, use_container_width=True, hide_index=True)
            else:
                st.caption("Query executed successfully — 0 rows returned.")

        st.session_state.history.append({
            "question":          query_to_run,
            "success":           True,
            "answer":            resp["answer"],
            "sql":               gen["sql"],
            "retrieved_tables":  retrieved_tables,
            "similarity_scores": similarity_scores,
            "rows":              serialize_rows(exe["rows"]),
            "row_count":         exe["row_count"],
            "truncated":         exe["truncated"],
            "error":             "",
        })

        st.rerun()
