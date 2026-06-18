"""
Prepare cleaned Telco churn data for MySQL analysis.

Adds SQL-friendly columns:
- snake_case naming
- plan_type (contract)
- join_date / churn_date / churn_month (derived timeline for monthly churn)
- risk_score, engagement_score, tenure_group
- is_high_value, basic_cltv_calc
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from feature_engineering import engineer_features  # noqa: E402

CLEANED_PATH = ROOT / "Telco_customer_churn_cleaned.csv"
OUTPUT_PATH = ROOT / "sql" / "telco_customers_sql_ready.csv"
REFERENCE_DATE = datetime(2026, 1, 1)


def _signup_offset(customer_id: str) -> int:
    """Stable 0-35 month offset so churn events spread across calendar months."""
    digest = hashlib.md5(customer_id.encode(), usedforsecurity=False).hexdigest()
    return int(digest[:8], 16) % 36


def prepare_for_sql(df: pd.DataFrame) -> pd.DataFrame:
    """Transform cleaned + engineered data into a MySQL-ready dataframe."""
    out = engineer_features(df)

    out = out.rename(
        columns={
            "CustomerID": "customer_id",
            "Count": "customer_count",
            "Country": "country",
            "State": "state",
            "City": "city",
            "Zip Code": "zip_code",
            "Lat Long": "lat_long",
            "Latitude": "latitude",
            "Longitude": "longitude",
            "Gender": "gender",
            "Senior Citizen": "senior_citizen",
            "Partner": "partner",
            "Dependents": "dependents",
            "Tenure Months": "tenure_months",
            "Phone Service": "phone_service",
            "Multiple Lines": "multiple_lines",
            "Internet Service": "internet_service",
            "Online Security": "online_security",
            "Online Backup": "online_backup",
            "Device Protection": "device_protection",
            "Tech Support": "tech_support",
            "Streaming TV": "streaming_tv",
            "Streaming Movies": "streaming_movies",
            "Contract": "contract",
            "Paperless Billing": "paperless_billing",
            "Payment Method": "payment_method",
            "Monthly Charges": "monthly_charges",
            "Total Charges": "total_charges",
            "Churn Label": "churn_label",
            "Churn Value": "churn_value",
            "Churn Score": "churn_score",
            "CLTV": "cltv",
            "Churn Reason": "churn_reason",
        }
    )

    out["plan_type"] = out["contract"]
    out["reference_date"] = REFERENCE_DATE.date()

    offsets = out["customer_id"].map(_signup_offset)
    total_months_back = out["tenure_months"] + offsets
    out["join_date"] = [
        (REFERENCE_DATE - pd.DateOffset(months=int(m))).date()
        for m in total_months_back
    ]
    out["join_month"] = pd.to_datetime(out["join_date"]).dt.to_period("M").astype(str)

    churned = out["churn_value"] == 1
    churn_dates = []
    for join, tenure, is_churned in zip(
        out["join_date"], out["tenure_months"], churned
    ):
        if is_churned:
            churn_dates.append(
                (pd.Timestamp(join) + pd.DateOffset(months=int(tenure))).date()
            )
        else:
            churn_dates.append(None)
    out["churn_date"] = churn_dates
    out["churn_month"] = pd.to_datetime(out["churn_date"], errors="coerce").dt.to_period(
        "M"
    ).astype(str)
    out.loc[~churned, "churn_month"] = None

    cltv_p75 = out["cltv"].quantile(0.75)
    monthly_p75 = out["monthly_charges"].quantile(0.75)
    out["is_high_value"] = (
        (out["cltv"] >= cltv_p75) | (out["monthly_charges"] >= monthly_p75)
    ).astype(int)

    out["basic_cltv_calc"] = out["monthly_charges"] * out["tenure_months"]

    out["risk_segment"] = pd.cut(
        out["risk_score"],
        bins=[0, 40, 65, 100],
        labels=["Low Risk", "Medium Risk", "High Risk"],
        include_lowest=True,
    )

    return out


def main() -> None:
    df = pd.read_csv(CLEANED_PATH)
    prepared = prepare_for_sql(df)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prepared.to_csv(OUTPUT_PATH, index=False)

    print(f"Input rows: {len(df)}")
    print(f"Output rows: {len(prepared)}")
    print(f"Columns: {len(prepared.columns)}")
    print(f"Saved: {OUTPUT_PATH}")
    print("\nSQL-specific columns added:")
    for col in [
        "plan_type",
        "join_date",
        "join_month",
        "churn_date",
        "churn_month",
        "reference_date",
        "is_high_value",
        "basic_cltv_calc",
        "risk_segment",
    ]:
        print(f"  - {col}")


if __name__ == "__main__":
    main()
