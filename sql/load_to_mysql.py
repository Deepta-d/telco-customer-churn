"""Load SQL-ready Telco churn CSV into MySQL."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import math

import numpy as np
import pandas as pd

try:
    import pymysql
except ImportError:
    print("Install pymysql: pip install pymysql")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = Path(__file__).resolve().parent
CSV_PATH = SQL_DIR / "telco_customers_sql_ready.csv"
SCHEMA_PATH = SQL_DIR / "schema.sql"

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "telco_churn"),
    "charset": "utf8mb4",
}


def _connect(with_db: bool = True) -> pymysql.Connection:
    kwargs = {**DB_CONFIG}
    if not with_db:
        kwargs.pop("database", None)
    if not kwargs.get("password"):
        raise ValueError(
            "MySQL password not set. Set MYSQL_PASSWORD environment variable, "
            "or create sql/.env with MYSQL_PASSWORD=your_password"
        )
    return pymysql.connect(**kwargs)


def _load_env_file() -> None:
    env_path = SQL_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def run_schema() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
    conn = _connect(with_db=False)
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
        print("Schema created: telco_churn.telco_customers")
    finally:
        conn.close()


def _sanitize(value):
    """Convert pandas/numpy nulls and NaN to None for MySQL."""
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


def load_data() -> int:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"{CSV_PATH} not found. Run: python sql/prepare_sql_dataset.py"
        )

    df = pd.read_csv(CSV_PATH)
    date_cols = ["reference_date", "join_date", "churn_date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df = df.where(pd.notna(df), None)

    # Convert pandas timestamps to Python dates for MySQL
    for col in date_cols:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: x.date() if hasattr(x, "date") and pd.notna(x) else x
            )

    conn = _connect(with_db=True)
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE telco_customers")
            columns = list(df.columns)
            placeholders = ", ".join(["%s"] * len(columns))
            col_names = ", ".join(f"`{c}`" for c in columns)
            sql = f"INSERT INTO telco_customers ({col_names}) VALUES ({placeholders})"

            rows = [
                tuple(_sanitize(v) for v in row)
                for row in df.itertuples(index=False, name=None)
            ]
            batch_size = 500
            for i in range(0, len(rows), batch_size):
                cur.executemany(sql, rows[i : i + batch_size])
        conn.commit()
        print(f"Loaded {len(df)} rows into telco_churn.telco_customers")
        return len(df)
    finally:
        conn.close()


def verify() -> None:
    conn = _connect(with_db=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM telco_customers")
            count = cur.fetchone()[0]
            cur.execute(
                "SELECT plan_type, ROUND(AVG(churn_value)*100,2) "
                "FROM telco_customers GROUP BY plan_type"
            )
            churn_by_plan = cur.fetchall()
        print(f"\nVerification: {count} rows in table")
        print("Churn by plan type:")
        for plan, rate in churn_by_plan:
            print(f"  {plan}: {rate}%")
    finally:
        conn.close()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Load Telco churn data into MySQL")
    parser.add_argument("--password", "-p", help="MySQL password (overrides .env)")
    args = parser.parse_args()

    _load_env_file()
    DB_CONFIG["host"] = os.getenv("MYSQL_HOST", DB_CONFIG["host"])
    DB_CONFIG["port"] = int(os.getenv("MYSQL_PORT", str(DB_CONFIG["port"])))
    DB_CONFIG["user"] = os.getenv("MYSQL_USER", DB_CONFIG["user"])
    DB_CONFIG["password"] = args.password or os.getenv("MYSQL_PASSWORD", DB_CONFIG["password"])
    DB_CONFIG["database"] = os.getenv("MYSQL_DATABASE", DB_CONFIG["database"])

    run_schema()
    load_data()
    verify()


if __name__ == "__main__":
    main()
