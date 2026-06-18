"""Phase 5 GenAI Churn Copilot — config, tools, prompts, and LangGraph agent."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from sqlalchemy import create_engine, text
from typing_extensions import Annotated, TypedDict

ROOT = Path(__file__).resolve().parent.parent
GENAI_DIR = Path(__file__).resolve().parent
SQL_DIR = ROOT / "sql"

ALLOWED_TABLES = {"telco_customers", "vw_powerbi_customers", "churn_scores_full"}
FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

SEGMENT_COLUMNS = {
    "plan": "plan_type",
    "plan_type": "plan_type",
    "contract": "plan_type",
    "city": "city",
    "region": "city",
    "gender": "gender",
    "senior": "senior_citizen",
    "age": "age_segment",
    "internet": "internet_service",
    "payment": "payment_method",
}


def load_env() -> None:
    load_dotenv(GENAI_DIR / ".env")
    load_dotenv(SQL_DIR / ".env")


def get_config() -> dict[str, str]:
    load_env()
    return {
        "llm_provider": os.getenv("LLM_PROVIDER", "openai").lower(),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.2"),
        "mysql_host": os.getenv("MYSQL_HOST", "localhost"),
        "mysql_port": os.getenv("MYSQL_PORT", "3306"),
        "mysql_user": os.getenv("MYSQL_USER", "root"),
        "mysql_password": os.getenv("MYSQL_PASSWORD", ""),
        "mysql_database": os.getenv("MYSQL_DATABASE", "telco_churn"),
    }


def get_engine():
    cfg = get_config()
    if not cfg["mysql_password"]:
        raise ValueError(
            "MySQL password not set. Add MYSQL_PASSWORD to genai/.env or sql/.env"
        )
    user = quote_plus(cfg["mysql_user"])
    password = quote_plus(cfg["mysql_password"])
    host = cfg["mysql_host"]
    port = cfg["mysql_port"]
    database = cfg["mysql_database"]
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url, pool_pre_ping=True)


def test_mysql_connection() -> dict[str, Any]:
    engine = get_engine()
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM telco_customers")).scalar()
        view_count = conn.execute(
            text("SELECT COUNT(*) FROM vw_powerbi_customers")
        ).scalar()
    return {
        "ok": True,
        "telco_customers": int(count),
        "vw_powerbi_customers": int(view_count),
    }


def load_context() -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    eda_path = ROOT / "eda_outputs" / "eda_stats.json"
    phase3_path = ROOT / "ml_outputs" / "phase3_summary.json"
    shap_path = ROOT / "ml_outputs" / "shap" / "shap_top_features.csv"

    if eda_path.exists():
        ctx["eda"] = json.loads(eda_path.read_text(encoding="utf-8"))
    if phase3_path.exists():
        ctx["phase3"] = json.loads(phase3_path.read_text(encoding="utf-8"))
    if shap_path.exists():
        ctx["shap_top"] = pd.read_csv(shap_path).head(10).to_dict(orient="records")
    return ctx


def validate_sql(query: str) -> str:
    q = query.strip().rstrip(";")
    if not q.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")
    if FORBIDDEN_SQL.search(q):
        raise ValueError("Query contains forbidden SQL keywords.")
    tables = set(re.findall(r"\b(?:FROM|JOIN)\s+`?(\w+)`?", q, re.IGNORECASE))
    bad = tables - ALLOWED_TABLES
    if bad:
        raise ValueError(f"Tables not allowed: {bad}. Use: {ALLOWED_TABLES}")
    if "LIMIT" not in q.upper():
        q = f"{q} LIMIT 500"
    return q


def run_query(query: str) -> pd.DataFrame:
    safe = validate_sql(query)
    engine = get_engine()
    return pd.read_sql(text(safe), engine)


def df_to_markdown(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "_No rows returned._"
    preview = df.head(max_rows)
    return preview.to_markdown(index=False)


def build_system_prompt(context: dict[str, Any] | None = None) -> str:
    context = context or load_context()
    eda = context.get("eda", {})
    phase3 = context.get("phase3", {})
    churn_rate = eda.get("churn", {}).get("overall_churn_rate_pct", "26.54")
    shap_lines = []
    for item in phase3.get("top_shap_features", [])[:8]:
        shap_lines.append(f"- {item.get('feature', '')}")

    schema = """
Allowed MySQL tables:
- telco_customers: customer_id, plan_type, contract, gender, senior_citizen, city, state,
  tenure_months, monthly_charges, churn_label, churn_value, churn_reason, churn_month,
  join_month, internet_service, payment_method, risk_score, engagement_score
- vw_powerbi_customers: all telco_customers columns plus churn_risk_pct, risk_tier,
  age_segment, usage_band, revenue_at_risk, top10_risk_rank
- churn_scores_full: customer_id, churn_risk_pct, risk_tier, predicted_churn

Note: join_month and churn_month are synthetic cohort months (Phase 2), not live calendar dates.
"""

    few_shot = """
Example Q: Which plan has the highest churn?
→ Use get_segment_churn with segment_column=plan_type, then summarize the highest churn_rate_pct.

Example Q: Why are customers churning?
→ Use get_churn_summary for ML/EDA drivers, then run_sql_query on churn_reason counts.

Example Q: What is the churn trend last 3 months?
→ Use get_churn_trend with last_n_months=3, then generate_chart with chart_type=line and SQL on churn_month.

Example Q: Show churn rate by plan as a chart
→ Use get_segment_churn or SQL, then generate_chart with chart_type=bar.

Charts:
- For trends over time → generate_chart(chart_type="line", ...)
- For comparing segments (plan, city, gender) → generate_chart(chart_type="bar", ...)
- For proportions / mix → generate_chart(chart_type="pie", ...)
- SQL for charts must return exactly 2 columns: label + numeric value
- Call generate_chart when the user asks to "show", "plot", "chart", or "visualize" data
"""

    return f"""You are a Telco Customer Churn analytics copilot for business users.

{schema}

Known baseline facts:
- Total customers: {eda.get('dataset_rows', 7043)}
- Overall churn rate: {churn_rate}%
- Month-to-month contracts have the highest churn (~43% in this dataset)
- Fiber optic internet customers churn more than DSL

Top ML churn drivers (CatBoost SHAP):
{chr(10).join(shap_lines) if shap_lines else '- contract, tenure, fiber internet, electronic check'}

Rules:
1. Always use tools to fetch numbers; never invent metrics.
2. Cite segment names and percentages from tool results.
3. If data is insufficient, say so clearly.
4. Keep answers concise and business-friendly (3-6 sentences plus bullet points if helpful).
5. For trend questions, mention churn_month is a derived cohort month.
6. When the user wants a visual, call generate_chart after fetching data with SQL.

{few_shot}
"""


# --- LangChain tools ---

_last_chart: dict[str, Any] = {}
_last_sql: str = ""


@tool
def run_sql_query(query: str) -> str:
    """Run a read-only SELECT on telco_churn tables. Returns results as a markdown table."""
    global _last_sql
    try:
        df = run_query(query)
        _last_sql = query
        return df_to_markdown(df)
    except Exception as exc:
        return f"SQL error: {exc}"


@tool
def get_churn_summary() -> str:
    """Return precomputed EDA stats, segmentation, and ML SHAP churn drivers."""
    ctx = load_context()
    eda = ctx.get("eda", {})
    phase3 = ctx.get("phase3", {})
    summary = {
        "overall_churn_rate_pct": eda.get("churn", {}).get("overall_churn_rate_pct"),
        "churn_breakdowns": eda.get("churn_breakdowns", {}),
        "risk_segments": eda.get("segmentation", {}),
        "top_correlations": eda.get("correlations", {}),
        "shap_top_features": phase3.get("top_shap_features", [])[:10],
        "best_model": phase3.get("best_model"),
        "model_roc_auc": phase3.get("test_metrics", {}).get("roc_auc"),
    }
    return json.dumps(summary, indent=2)


@tool
def get_segment_churn(segment_column: str) -> str:
    """Churn rate by segment. segment_column: plan_type, city, gender, senior_citizen, age_segment, internet_service, payment_method."""
    col = SEGMENT_COLUMNS.get(segment_column.lower(), segment_column)
    allowed = set(SEGMENT_COLUMNS.values()) | {"age_segment"}
    if col not in allowed:
        return f"Invalid segment. Use one of: {sorted(allowed)}"
    query = f"""
    SELECT {col} AS segment,
           COUNT(*) AS total_customers,
           SUM(churn_value) AS churned,
           ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
    FROM vw_powerbi_customers
    GROUP BY {col}
    ORDER BY churn_rate_pct DESC
    """
    df = run_query(query)
    return df_to_markdown(df)


@tool
def get_churn_trend(last_n_months: int = 6) -> str:
    """Monthly churn counts and rates by churn_month. Use last_n_months to limit (e.g. 3 for last 3 months)."""
    n = max(1, min(int(last_n_months), 24))
    query = f"""
    SELECT churn_month,
           COUNT(*) AS churned_customers,
           ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges_lost
    FROM telco_customers
    WHERE churn_value = 1 AND churn_month IS NOT NULL
    GROUP BY churn_month
    ORDER BY churn_month DESC
    LIMIT {n}
    """
    df = run_query(query)
    return df_to_markdown(df.sort_values("churn_month"))


@tool
def get_top_risk_customers(limit: int = 10) -> str:
    """Top active (not churned) customers by ML churn_risk_pct."""
    n = max(1, min(int(limit), 50))
    query = f"""
    SELECT customer_id, churn_risk_pct, monthly_charges, plan_type, city,
           tenure_months, internet_service
    FROM vw_powerbi_customers
    WHERE churn_label = 'No'
    ORDER BY churn_risk_pct DESC
    LIMIT {n}
    """
    df = run_query(query)
    return df_to_markdown(df)


@tool
def generate_chart(chart_type: str, sql_query: str, title: str = "Chart") -> str:
    """Create a Plotly chart from SQL results. chart_type: bar, line, or pie. Returns confirmation message; chart stored for UI."""
    global _last_chart, _last_sql
    try:
        df = run_query(sql_query)
        _last_sql = sql_query
        if df.empty or len(df.columns) < 2:
            return "Not enough data to chart (need at least 2 columns)."

        x_col, y_col = df.columns[0], df.columns[1]
        ctype = chart_type.lower().strip()

        if ctype == "line":
            fig = px.line(df, x=x_col, y=y_col, title=title, markers=True)
        elif ctype == "pie":
            fig = px.pie(df, names=x_col, values=y_col, title=title)
        else:
            fig = px.bar(df, x=x_col, y=y_col, title=title, text=y_col)

        fig.update_layout(template="plotly_white", height=400)
        _last_chart = {"figure": fig, "title": title}
        return f"Chart '{title}' created with {len(df)} rows ({ctype})."
    except Exception as exc:
        return f"Chart error: {exc}"


TOOLS = [
    run_sql_query,
    get_churn_summary,
    get_segment_churn,
    get_churn_trend,
    get_top_risk_customers,
    generate_chart,
]


def get_llm():
    cfg = get_config()
    provider = cfg["llm_provider"]

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            base_url=cfg["ollama_base_url"],
            model=cfg["ollama_model"],
            temperature=0,
        )

    from langchain_openai import ChatOpenAI

    if not cfg["openai_api_key"]:
        raise ValueError("OPENAI_API_KEY not set in genai/.env")
    return ChatOpenAI(
        model=cfg["openai_model"],
        api_key=cfg["openai_api_key"],
        temperature=0,
    )


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def build_graph():
    llm = get_llm().bind_tools(TOOLS)
    tool_node = ToolNode(TOOLS)

    def agent_node(state: AgentState):
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "end"

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")
    return graph.compile()


def ask(question: str, chat_history: list | None = None) -> dict[str, Any]:
    """Run the agent on a question. Returns answer text and optional chart."""
    global _last_chart, _last_sql
    _last_chart = {}
    _last_sql = ""

    graph = build_graph()
    messages = [SystemMessage(content=build_system_prompt())]
    if chat_history:
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=question))

    try:
        result = graph.invoke({"messages": messages})
    except Exception as exc:
        raise RuntimeError(_friendly_llm_error(exc)) from exc

    final = result["messages"][-1]
    answer = final.content if isinstance(final, AIMessage) else str(final)

    out: dict[str, Any] = {
        "answer": answer,
        "sql": _last_sql,
        "chart": _last_chart.get("figure"),
        "chart_title": _last_chart.get("title", ""),
    }
    return out


def _friendly_llm_error(exc: Exception, cfg: dict[str, str] | None = None) -> str:
    cfg = cfg or get_config()
    msg = str(exc)
    if cfg.get("llm_provider") == "ollama" and (
        "10061" in msg or "Connection refused" in msg or "actively refused" in msg
    ):
        return (
            "Ollama is not running. Start the Ollama app (or run `ollama serve`), "
            f"then pull the model: `ollama pull {cfg.get('ollama_model', 'llama3.2')}`. "
            f"Expected API at {cfg.get('ollama_base_url', 'http://localhost:11434')}. "
            "Alternatively, set LLM_PROVIDER=openai and OPENAI_API_KEY in genai/.env."
        )
    if "OPENAI_API_KEY" in msg or (
        cfg.get("llm_provider") == "openai"
        and ("api_key" in msg.lower() or "sk-your-key" in cfg.get("openai_api_key", ""))
    ):
        return (
            "OpenAI API key missing or invalid. Set OPENAI_API_KEY in genai/.env "
            "or switch to LLM_PROVIDER=ollama with Ollama running."
        )
    return msg


def test_llm_connection() -> dict[str, Any]:
    cfg = get_config()
    try:
        llm = get_llm()
        resp = llm.invoke("Reply with exactly: OK")
        content = resp.content if hasattr(resp, "content") else str(resp)
        return {"ok": True, "provider": cfg["llm_provider"], "response": content[:50]}
    except Exception as exc:
        return {
            "ok": False,
            "provider": cfg["llm_provider"],
            "error": _friendly_llm_error(exc, cfg),
        }
