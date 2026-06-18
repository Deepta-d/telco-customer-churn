"""
Phase 2 setup — load Telco churn data into MySQL and run queries.

Usage (recommended — no PowerShell script policy issues):
    python sql/setup_phase2.py

With password on command line:
    python sql/setup_phase2.py -p "your_mysql_password"

Or create sql/.env with MYSQL_PASSWORD=your_password and run:
    python sql/setup_phase2.py
"""

from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent
ROOT = SQL_DIR.parent


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


def _run_step(label: str, cmd: list[str], env: dict | None = None) -> None:
    print(f"\n{'=' * 60}")
    print(label)
    print("=" * 60)
    result = subprocess.run(cmd, cwd=ROOT, env=env)
    if result.returncode != 0:
        print(f"\nFailed: {' '.join(cmd)}")
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 MySQL setup for Telco churn")
    parser.add_argument("-p", "--password", help="MySQL root password")
    args = parser.parse_args()

    _load_env_file()
    password = args.password or os.getenv("MYSQL_PASSWORD")

    if not password or password == "your_password_here":
        print("MySQL password required.")
        print("Tip: create sql/.env from sql/.env.example and set MYSQL_PASSWORD")
        password = getpass.getpass("Enter MySQL password: ")

    if not password:
        print("No password provided. Exiting.")
        sys.exit(1)

    env = os.environ.copy()
    env["MYSQL_PASSWORD"] = password

    _run_step(
        "Step 1: Prepare SQL-ready dataset",
        [sys.executable, str(SQL_DIR / "prepare_sql_dataset.py")],
    )
    _run_step(
        "Step 2: Load into MySQL",
        [sys.executable, str(SQL_DIR / "load_to_mysql.py"), "-p", password],
    )
    _run_step(
        "Step 3: Run analysis queries",
        [sys.executable, str(SQL_DIR / "run_queries.py")],
        env=env,
    )

    print("\nPhase 2 complete.")


if __name__ == "__main__":
    main()
