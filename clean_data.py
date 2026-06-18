"""Clean Telco customer churn dataset: handle missing values and remove duplicates."""

from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).parent / "Telco_customer_churn.xlsx"
OUTPUT_PATH = Path(__file__).parent / "Telco_customer_churn_cleaned.csv"


def clean_telco_churn(df: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy of the Telco churn dataframe."""
    cleaned = df.copy()

    # Remove duplicate rows and duplicate customer IDs
    before = len(cleaned)
    cleaned = cleaned.drop_duplicates()
    cleaned = cleaned.drop_duplicates(subset=["CustomerID"], keep="first")
    duplicates_removed = before - len(cleaned)

    # Total Charges: 11 rows store whitespace for new customers (tenure = 0 months)
    cleaned["Total Charges"] = (
        cleaned["Total Charges"]
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
    )
    cleaned["Total Charges"] = pd.to_numeric(cleaned["Total Charges"], errors="coerce")
    tenure_zero_mask = cleaned["Tenure Months"] == 0
    cleaned.loc[tenure_zero_mask & cleaned["Total Charges"].isna(), "Total Charges"] = 0.0

    # Churn Reason is only recorded for churned customers
    non_churned = cleaned["Churn Label"].str.strip().str.lower() == "no"
    cleaned.loc[non_churned & cleaned["Churn Reason"].isna(), "Churn Reason"] = (
        "Not Applicable"
    )

    return cleaned, duplicates_removed


def main() -> None:
    df = pd.read_excel(DATA_PATH)
    print(f"Loaded: {df.shape[0]} rows, {df.shape[1]} columns")

    cleaned, duplicates_removed = clean_telco_churn(df)

    missing_before = df.isna().sum().sum()
    # Include whitespace-only Total Charges as missing before cleaning
    total_charges_whitespace = (
        df["Total Charges"].astype(str).str.strip().eq("").sum()
    )
    missing_after = cleaned.isna().sum().sum()

    cleaned.to_csv(OUTPUT_PATH, index=False)

    print(f"Duplicates removed: {duplicates_removed}")
    print(f"Total Charges whitespace fixed: {total_charges_whitespace}")
    print(f"Churn Reason filled for non-churned: {non_churned_count(df)}")
    print(f"Missing values before: {missing_before + total_charges_whitespace}")
    print(f"Missing values after: {missing_after}")
    print(f"Saved cleaned data to: {OUTPUT_PATH}")


def non_churned_count(df: pd.DataFrame) -> int:
    non_churned = df["Churn Label"].str.strip().str.lower() == "no"
    return int((non_churned & df["Churn Reason"].isna()).sum())


if __name__ == "__main__":
    main()
