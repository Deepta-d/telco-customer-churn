"""Validate SQL queries — run all or only queries from a given number."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    import pymysql
except ImportError:
    print("Install pymysql: pip install pymysql")
    sys.exit(1)

from run_queries import _load_env_file, _query_number, _split_queries

SQL_DIR = Path(__file__).resolve().parent
QUERIES_PATH = SQL_DIR / "analysis_queries.sql"

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "telco_churn"),
    "charset": "utf8mb4",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate analysis_queries.sql")
    parser.add_argument(
        "--from",
        dest="from_num",
        type=int,
        default=1,
        help="Only run queries numbered >= this (e.g. 7 for new queries only)",
    )
    args = parser.parse_args()

    _load_env_file()
    DB_CONFIG["password"] = os.getenv("MYSQL_PASSWORD", DB_CONFIG["password"])
    if not DB_CONFIG["password"]:
        print("Set MYSQL_PASSWORD in sql/.env")
        sys.exit(1)

    all_queries = _split_queries(QUERIES_PATH.read_text(encoding="utf-8"))
    queries = [
        (t, q) for t, q in all_queries if (_query_number(t) or 0) >= args.from_num
    ]

    passed = 0
    failed: list[tuple[str, str]] = []

    conn = pymysql.connect(**DB_CONFIG)
    try:
        for title, query in queries:
            try:
                with conn.cursor() as cur:
                    cur.execute(query)
                    rows = cur.fetchall() if cur.description else []
                print(f"  OK  [{title}] — {len(rows)} rows")
                passed += 1
            except Exception as exc:
                print(f"  FAIL [{title}] — {exc}")
                failed.append((title, str(exc)))
    finally:
        conn.close()

    print(f"\n{'=' * 60}")
    print(f"Passed: {passed}/{len(queries)}")
    if failed:
        print(f"Failed: {len(failed)}")
        for title, err in failed:
            print(f"  - {title}: {err}")
        sys.exit(1)
    print("All queries executed successfully.")


if __name__ == "__main__":
    main()
