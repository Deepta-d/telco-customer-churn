"""Feature engineering for Telco customer churn dataset."""

from pathlib import Path

import numpy as np
import pandas as pd

INPUT_PATH = Path(__file__).parent / "Telco_customer_churn_cleaned.csv"
OUTPUT_PATH = Path(__file__).parent / "Telco_customer_churn_engineered.csv"

YES_NO_MAP = {"Yes": 1, "No": 0}
CONTRACT_ORDINAL = {"Month-to-month": 0, "One year": 1, "Two year": 2}
TENURE_BINS = [0, 12, 36, 72]
TENURE_LABELS = ["New", "Established", "Loyal"]

ADDON_COLUMNS = [
    "Online Security",
    "Online Backup",
    "Device Protection",
    "Tech Support",
]
STREAMING_COLUMNS = ["Streaming TV", "Streaming Movies"]


def _yes_no(series: pd.Series) -> pd.Series:
    return series.map(YES_NO_MAP).fillna(0).astype(int)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add engineered features to the cleaned Telco churn dataframe."""
    out = df.copy()
    tenure = out["Tenure Months"].clip(lower=0)

    out["tenure_group"] = pd.cut(
        tenure,
        bins=TENURE_BINS,
        labels=TENURE_LABELS,
        include_lowest=True,
        right=True,
    )
    out["avg_monthly_spend"] = out["Total Charges"] / tenure.replace(0, np.nan)
    out["avg_monthly_spend"] = out["avg_monthly_spend"].fillna(out["Monthly Charges"])
    out["charge_drift"] = out["Monthly Charges"] - out["avg_monthly_spend"]
    out["cltv_per_month"] = out["CLTV"] / tenure.replace(0, 1)

    out["is_senior"] = _yes_no(out["Senior Citizen"])
    out["has_partner"] = _yes_no(out["Partner"])
    out["has_dependents"] = _yes_no(out["Dependents"])
    out["household_size_proxy"] = 1 + out["has_partner"] + out["has_dependents"]
    out["family_household"] = (
        (out["Partner"] == "Yes") | (out["Dependents"] == "Yes")
    ).astype(int)

    out["contract_ordinal"] = out["Contract"].map(CONTRACT_ORDINAL).fillna(0).astype(int)
    out["is_month_to_month"] = (out["Contract"] == "Month-to-month").astype(int)
    out["is_paperless"] = _yes_no(out["Paperless Billing"])
    out["is_autopay"] = out["Payment Method"].isin(
        ["Bank transfer (automatic)", "Credit card (automatic)"]
    ).astype(int)
    out["is_electronic_check"] = (
        out["Payment Method"] == "Electronic check"
    ).astype(int)

    out["internet_fiber"] = (out["Internet Service"] == "Fiber optic").astype(int)
    out["internet_dsl"] = (out["Internet Service"] == "DSL").astype(int)
    out["no_internet"] = (out["Internet Service"] == "No").astype(int)
    out["has_phone"] = _yes_no(out["Phone Service"])
    out["has_multiple_lines"] = (out["Multiple Lines"] == "Yes").astype(int)

    out["addon_services_count"] = sum(_yes_no(out[col]) for col in ADDON_COLUMNS)
    out["streaming_services_count"] = sum(
        _yes_no(out[col]) for col in STREAMING_COLUMNS
    )
    out["total_services_count"] = (
        out["addon_services_count"] + out["streaming_services_count"]
    )
    out["has_streaming_bundle"] = (out["streaming_services_count"] >= 2).astype(int)

    monthly_p75 = out["Monthly Charges"].quantile(0.75)
    out["high_monthly_charge"] = (out["Monthly Charges"] >= monthly_p75).astype(int)

    out["engagement_score"] = (
        out["contract_ordinal"] * 25
        + (tenure / 72) * 25
        + out["addon_services_count"] * 5
        + out["is_autopay"] * 10
    ).clip(0, 100)
    out["risk_score"] = (
        100
        - out["engagement_score"]
        + out["is_month_to_month"] * 15
        + out["internet_fiber"] * 10
        + out["is_electronic_check"] * 10
        + out["high_monthly_charge"] * 5
        + out["is_senior"] * 5
    ).clip(0, 100)

    return out


def added_feature_names() -> list[str]:
    """Return names of engineered features (not in original cleaned dataset)."""
    original = pd.read_csv(INPUT_PATH, nrows=1).columns.tolist()
    engineered = engineer_features(pd.read_csv(INPUT_PATH, nrows=5)).columns.tolist()
    return [col for col in engineered if col not in original]


def main() -> None:
    df = pd.read_csv(INPUT_PATH)
    engineered = engineer_features(df)
    engineered.to_csv(OUTPUT_PATH, index=False)

    new_features = added_feature_names()
    print(f"Input shape: {df.shape}")
    print(f"Output shape: {engineered.shape}")
    print(f"Features added ({len(new_features)}):")
    for name in new_features:
        print(f"  - {name}")
    print(f"\nSaved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
