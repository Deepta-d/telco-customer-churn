"""Run full Phase 4 data pipeline for Power BI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4 Power BI data setup")
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="Force re-score all customers with CatBoost",
    )
    parser.add_argument(
        "--skip-mysql",
        action="store_true",
        help="Skip MySQL view and score load",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "powerbi"))
    from prepare_powerbi_dataset import build_powerbi_dataset

    print("=== Phase 4: Power BI Data Setup ===\n")
    build_powerbi_dataset(rescore=args.rescore)

    if not args.skip_mysql:
        try:
            from load_scores_to_mysql import load_scores, run_views_sql, verify

            run_views_sql()
            load_scores()
            verify()
        except Exception as exc:
            print(f"MySQL step skipped or failed: {exc}")
            print("CSV dataset is ready for Power BI import.")

    print("\nNext: Open Power BI Desktop and follow powerbi/DASHBOARD_BUILD_GUIDE.md")


if __name__ == "__main__":
    main()
