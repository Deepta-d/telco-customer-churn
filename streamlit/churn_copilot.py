"""Streamlit entry point for Telco Churn AI Copilot (Phase 5)."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from genai.copilot import (  # noqa: E402
    ask,
    get_config,
    test_llm_connection,
    test_mysql_connection,
)

SAMPLE_QUESTIONS = [
    "Why are customers churning?",
    "Which segment has highest churn?",
    "What is the churn trend last 3 months?",
    "Who are the top 10 customers at risk?",
    "What is ARPU by plan?",
    "How does churn differ for senior vs non-senior?",
    "Which city has highest churn?",
    "What is the overall churn rate?",
]

CHART_EXAMPLE_QUESTIONS = [
    "Show a bar chart of churn rate by plan type",
    "Chart the churn trend for the last 6 months",
    "Plot churn rate by internet service as a pie chart",
]


def _run_agent(prompt: str) -> None:
    """Call the LangGraph agent and append the assistant reply to session state."""
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ]
    result = ask(prompt, chat_history=history)
    answer = result.get("answer", "No response.")
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "chart": result.get("chart"),
            "chart_title": result.get("chart_title", ""),
            "sql": result.get("sql", ""),
        }
    )


def main() -> None:
    st.set_page_config(
        page_title="Telco Churn AI Copilot",
        page_icon="📊",
        layout="wide",
    )

    st.title("Telco Churn AI Copilot")
    st.caption(
        "Ask business questions about churn — answers are grounded in your MySQL telco_churn data."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    llm_ready = False

    with st.sidebar:
        st.header("Status")
        cfg = get_config()
        st.write(f"**LLM:** {cfg['llm_provider']}")

        try:
            mysql_status = test_mysql_connection()
            st.success(f"MySQL OK — {mysql_status['telco_customers']:,} customers")
        except Exception as exc:
            st.error(f"MySQL: {exc}")

        llm_status = test_llm_connection()
        if llm_status.get("ok"):
            st.success(f"LLM OK ({llm_status['provider']})")
            llm_ready = True
        else:
            st.error("LLM not connected")
            st.caption(llm_status.get("error", "unavailable"))

        st.divider()
        st.subheader("Sample questions")
        for q in SAMPLE_QUESTIONS:
            if st.button(q, key=f"sample_{q[:30]}", use_container_width=True):
                st.session_state.pending_question = q

        st.divider()
        st.subheader("Chart examples")
        st.caption("Ask for a chart — the agent calls `generate_chart` with SQL + Plotly.")
        for q in CHART_EXAMPLE_QUESTIONS:
            if st.button(q, key=f"chart_{q[:24]}", use_container_width=True):
                st.session_state.pending_question = q

        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # --- Main question input (always visible at top) ---
    st.subheader("Ask a question")
    with st.form("main_ask_form", clear_on_submit=True):
        question_text = st.text_area(
            "Your question",
            placeholder=(
                "e.g. Why are customers churning? "
                "Or: Show a bar chart of churn rate by plan type"
            ),
            height=100,
            label_visibility="collapsed",
            disabled=not llm_ready,
        )
        submitted = st.form_submit_button(
            "Ask",
            type="primary",
            disabled=not llm_ready,
            use_container_width=False,
        )
        if submitted and question_text.strip():
            st.session_state.pending_question = question_text.strip()
            st.rerun()

    if not llm_ready:
        st.info("Connect Ollama or OpenAI to enable questions. See sidebar for status.")

    st.divider()

    # --- Chat history ---
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("chart") is not None:
                title = msg.get("chart_title") or "Chart"
                st.caption(f"📊 {title}")
                st.plotly_chart(msg["chart"], use_container_width=True)
            if msg.get("sql"):
                with st.expander("View SQL used"):
                    st.code(msg["sql"], language="sql")

    # --- Process pending prompt (from form, sidebar, or chat_input) ---
    pending = st.session_state.pop("pending_question", None)

    # Always render chat_input every run (fixes missing bottom bar after sample clicks)
    chat_typed = st.chat_input(
        "Or type here and press Enter…",
        disabled=not llm_ready,
    )

    prompt = pending or chat_typed

    if prompt and not llm_ready:
        st.error("Cannot answer until the LLM is connected. See sidebar for fix steps.")
    elif prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Analyzing…"):
            try:
                _run_agent(prompt)
            except Exception as exc:
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"Error: {exc}"}
                )
        st.rerun()


if __name__ == "__main__":
    main()
