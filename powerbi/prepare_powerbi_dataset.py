"""Build unified Power BI dataset from SQL-ready data and ML churn scores."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from score_full_dataset import score_full_dataset

ROOT = Path(__file__).resolve().parent.parent
SQL_READY_PATH = ROOT / "sql" / "telco_customers_sql_ready.csv"
SCORES_PATH = ROOT / "ml_outputs" / "churn_scores_full.csv"
OUTPUT_PATH = Path(__file__).resolve().parent / "telco_churn_powerbi.csv"


def usage_band(count: int) -> str:
    if count <= 2:
        return "Low (0-2)"
    if count <= 5:
        return "Medium (3-5)"
    return "High (6+)"


def age_segment(senior: str) -> str:
    return "Senior" if str(senior).strip().lower() == "yes" else "Non-Senior"


def build_powerbi_dataset(
    sql_ready_path: Path = SQL_READY_PATH,
    scores_path: Path = SCORES_PATH,
    output_path: Path = OUTPUT_PATH,
    rescore: bool = False,
) -> pd.DataFrame:
    if rescore or not scores_path.exists():
        score_full_dataset(output_path=scores_path)

    base = pd.read_csv(sql_ready_path)
    scores = pd.read_csv(scores_path)

    df = base.merge(scores, on="customer_id", how="left")
    if df["churn_risk_pct"].isna().any():
        missing = df["churn_risk_pct"].isna().sum()
        raise ValueError(f"Missing ML scores for {missing} customers after merge.")

    df["is_churned"] = df["churn_value"].astype(int)
    df["age_segment"] = df["senior_citizen"].map(age_segment)
    df["usage_band"] = df["total_services_count"].map(usage_band)
    df["tenure_band"] = df["tenure_group"].fillna("Unknown")
    df["region"] = df["city"]

    active_mask = df["churn_label"].str.lower() == "no"
    high_risk_mask = df["churn_risk_pct"] >= 70
    df["revenue_at_risk"] = df["monthly_charges"].where(active_mask & high_risk_mask, 0.0)

    active_risk = df.loc[active_mask].sort_values("churn_risk_pct", ascending=False)
    top10_ids = set(active_risk.head(10)["customer_id"])
    rank_map = {
        cid: rank
        for rank, cid in enumerate(active_risk.head(10)["customer_id"], start=1)
    }
    df["top10_risk_rank"] = df["customer_id"].map(rank_map)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"Power BI dataset: {len(df):,} rows x {df.shape[1]} columns -> {output_path}")
    print(f"Churn rate: {df['is_churned'].mean() * 100:.2f}%")
    print(f"Top 10 at-risk (active): {len(top10_ids)} customers ranked")
    return df


if __name__ == "__main__":
    rescore = "--rescore" in sys.argv
    try:
        build_powerbi_dataset(rescore=rescore)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
