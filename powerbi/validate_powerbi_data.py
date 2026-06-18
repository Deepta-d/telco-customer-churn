"""Validate Power BI dataset before dashboard build."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = Path(__file__).resolve().parent / "telco_churn_powerbi.csv"
SCORES_PATH = ROOT / "ml_outputs" / "churn_scores_full.csv"


def validate() -> bool:
    ok = True

    if not CSV_PATH.exists():
        print(f"FAIL: Missing {CSV_PATH}")
        return False

    df = pd.read_csv(CSV_PATH)
    scores = pd.read_csv(SCORES_PATH) if SCORES_PATH.exists() else None

    checks = [
        ("row_count", len(df) == 7043, f"rows={len(df)} (expected 7043)"),
        (
            "churn_rate",
            abs(df["is_churned"].mean() * 100 - 26.54) < 0.1,
            f"churn_rate={df['is_churned'].mean() * 100:.2f}%",
        ),
        (
            "ml_scores",
            df["churn_risk_pct"].isna().sum() == 0,
            f"null risk scores={df['churn_risk_pct'].isna().sum()}",
        ),
        (
            "required_cols",
            all(
                c in df.columns
                for c in [
                    "customer_id",
                    "churn_risk_pct",
                    "plan_type",
                    "gender",
                    "city",
                    "age_segment",
                    "usage_band",
                    "revenue_at_risk",
                    "top10_risk_rank",
                ]
            ),
            "dashboard columns present",
        ),
    ]

    active = df[df["churn_label"].str.lower() == "no"]
    top10 = (
        active.sort_values("churn_risk_pct", ascending=False)
        .head(10)[["customer_id", "churn_risk_pct"]]
    )
    top10_ranked = df[df["top10_risk_rank"].notna()]
    checks.append(
        (
            "top10",
            len(top10_ranked) == 10 and top10_ranked["churn_label"].str.lower().eq("no").all(),
            f"top10 ranked={len(top10_ranked)}",
        )
    )

    print("Power BI dataset validation\n" + "-" * 40)
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}: {detail}")
        ok = ok and passed

    if ok:
        print("\nTop 10 at-risk (active customers):")
        print(top10.to_string(index=False))
        print(f"\nAll checks passed. Import: {CSV_PATH}")
    else:
        print("\nFix issues with: python powerbi/setup_phase4.py --rescore")

    return ok


if __name__ == "__main__":
    sys.exit(0 if validate() else 1)
