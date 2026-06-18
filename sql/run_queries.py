"""Run Phase 2 SQL analysis queries and print results."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import pymysql
except ImportError:
    print("Install pymysql: pip install pymysql")
    sys.exit(1)

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


def _split_queries(sql_text: str) -> list[tuple[str, str]]:
    """Parse numbered query sections from analysis_queries.sql."""
    queries: list[tuple[str, str]] = []
    chunks = re.split(r"\n-- (\d+[a-z]?\.[^\n]+)\n", sql_text)

    for i in range(1, len(chunks), 2):
        title = chunks[i].strip()
        body = chunks[i + 1] if i + 1 < len(chunks) else ""
        body = "\n".join(
            line
            for line in body.splitlines()
            if not line.strip().startswith("--")
        )
        parts = re.split(r";\s*\n", body)
        for idx, part in enumerate(parts):
            stmt = part.strip().rstrip(";").strip()
            if not stmt:
                continue
            upper = stmt.upper()
            if not (upper.startswith("SELECT") or upper.startswith("WITH")):
                continue
            label = title if idx == 0 else f"{title} (part {idx + 1})"
            queries.append((label, stmt))

    return queries


def _query_number(title: str) -> int | None:
    match = re.match(r"^(\d+)", title)
    return int(match.group(1)) if match else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run analysis_queries.sql")
    parser.add_argument(
        "--from",
        dest="from_num",
        type=int,
        default=1,
        help="Only run queries numbered >= this value",
    )
    args = parser.parse_args()

    _load_env_file()
    DB_CONFIG["password"] = os.getenv("MYSQL_PASSWORD", DB_CONFIG["password"])
    if not DB_CONFIG["password"]:
        print("Set MYSQL_PASSWORD in sql/.env before running queries.")
        sys.exit(1)

    all_queries = _split_queries(QUERIES_PATH.read_text(encoding="utf-8"))
    queries = [
        (t, q) for t, q in all_queries if (_query_number(t) or 0) >= args.from_num
    ]

    conn = pymysql.connect(**DB_CONFIG)
    try:
        for title, query in queries:
            print("\n" + "=" * 70)
            print(title)
            print("=" * 70)
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
            if not rows:
                print("(no rows)")
                continue
            print(" | ".join(cols))
            print("-" * 70)
            for row in rows[:15]:
                print(" | ".join(str(v) for v in row))
            if len(rows) > 15:
                print(f"... {len(rows) - 15} more rows")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
