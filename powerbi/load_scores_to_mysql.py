"""Load ML churn scores and Power BI view into MySQL."""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import pymysql
except ImportError:
    print("Install pymysql: pip install pymysql")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql"
POWERBI_DIR = ROOT / "powerbi"
SCORES_CSV = ROOT / "ml_outputs" / "churn_scores_full.csv"
POWERBI_CSV = POWERBI_DIR / "telco_churn_powerbi.csv"
VIEWS_SQL = SQL_DIR / "powerbi_views.sql"

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "telco_churn"),
    "charset": "utf8mb4",
}


def _load_env_file() -> None:
    env_path = SQL_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _connect() -> pymysql.Connection:
    if not DB_CONFIG.get("password"):
        raise ValueError(
            "MySQL password not set. Create sql/.env with MYSQL_PASSWORD=your_password"
        )
    return pymysql.connect(**DB_CONFIG)


def _sanitize(value):
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (np.floating, np.integer)):
        if np.isnan(value):
            return None
        return value.item()
    if pd.isna(value):
        return None
    return value


def run_views_sql() -> None:
    sql_text = VIEWS_SQL.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]
    conn = _connect()
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
        print("Created churn_scores_full table and vw_powerbi_customers view")
    finally:
        conn.close()


def load_scores() -> int:
    if not SCORES_CSV.exists():
        raise FileNotFoundError(
            f"{SCORES_CSV} not found. Run: python powerbi/score_full_dataset.py"
        )

    df = pd.read_csv(SCORES_CSV)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE churn_scores_full")
            sql = (
                "INSERT INTO churn_scores_full "
                "(customer_id, churn_risk_pct, risk_tier, predicted_churn) "
                "VALUES (%s, %s, %s, %s)"
            )
            rows = [
                (
                    _sanitize(row.customer_id),
                    _sanitize(row.churn_risk_pct),
                    _sanitize(row.risk_tier),
                    int(row.predicted_churn),
                )
                for row in df.itertuples(index=False)
            ]
            cur.executemany(sql, rows)
        conn.commit()
        print(f"Loaded {len(df)} rows into churn_scores_full")
        return len(df)
    finally:
        conn.close()


def verify() -> None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM vw_powerbi_customers")
            count = cur.fetchone()[0]
            cur.execute(
                "SELECT ROUND(AVG(churn_risk_pct), 2), "
                "ROUND(SUM(CASE WHEN churn_label='Yes' THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) "
                "FROM vw_powerbi_customers"
            )
            avg_risk, churn_rate = cur.fetchone()
        print(f"vw_powerbi_customers: {count} rows")
        print(f"Avg churn risk: {avg_risk}% | Churn rate: {churn_rate}%")
    finally:
        conn.close()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Load Power BI ML scores into MySQL")
    parser.add_argument("--password", "-p", help="MySQL password (overrides .env)")
    args = parser.parse_args()

    _load_env_file()
    DB_CONFIG["password"] = args.password or os.getenv("MYSQL_PASSWORD", DB_CONFIG["password"])

    run_views_sql()
    load_scores()
    verify()


if __name__ == "__main__":
    main()
