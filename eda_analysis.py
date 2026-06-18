"""Exploratory data analysis for engineered Telco churn dataset."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from feature_engineering import INPUT_PATH, engineer_features

OUTPUT_DIR = Path(__file__).parent / "eda_outputs"
ENGINEERED_PATH = Path(__file__).parent / "Telco_customer_churn_engineered.csv"
STATS_PATH = OUTPUT_DIR / "eda_stats.json"

EXCLUDE_FROM_MODEL = {
    "CustomerID",
    "Count",
    "Country",
    "State",
    "City",
    "Zip Code",
    "Lat Long",
    "Latitude",
    "Longitude",
    "Churn Label",
    "Churn Value",
    "Churn Score",
    "Churn Reason",
    "tenure_group",
}

NUMERIC_FOR_CORR = [
    "Tenure Months",
    "Monthly Charges",
    "Total Charges",
    "CLTV",
    "avg_monthly_spend",
    "charge_drift",
    "cltv_per_month",
    "addon_services_count",
    "streaming_services_count",
    "total_services_count",
    "contract_ordinal",
    "risk_score",
    "engagement_score",
    "household_size_proxy",
    "Churn Value",
]


def _ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def churn_distribution(df: pd.DataFrame) -> dict:
    counts = df["Churn Label"].value_counts()
    rates = df["Churn Label"].value_counts(normalize=True) * 100
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    colors = ["#4C78A8", "#E45756"]
    axes[0].bar(counts.index, counts.values, color=colors)
    axes[0].set_title("Churn Count")
    axes[0].set_ylabel("Customers")
    axes[0].set_xlabel("Churn Label")

    axes[1].pie(
        counts.values,
        labels=[f"{label} ({rates[label]:.1f}%)" for label in counts.index],
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
    )
    axes[1].set_title("Churn Rate")

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "churn_distribution.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    return {
        "counts": {k: int(v) for k, v in counts.items()},
        "rates_pct": {k: round(float(v), 2) for k, v in rates.items()},
        "overall_churn_rate_pct": round(float(rates.get("Yes", 0)), 2),
    }


def correlation_heatmap(df: pd.DataFrame) -> dict:
    corr_df = df[NUMERIC_FOR_CORR].corr()
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(
        corr_df,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=0,
        square=True,
        linewidths=0.5,
        ax=ax,
    )
    ax.set_title("Feature Correlation Heatmap")
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "correlation_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    churn_corr = (
        corr_df["Churn Value"]
        .drop("Churn Value")
        .abs()
        .sort_values(ascending=False)
        .head(8)
    )
    return {
        "top_churn_correlations": {
            k: round(float(v), 3) for k, v in churn_corr.items()
        }
    }


def feature_importance(df: pd.DataFrame) -> dict:
    target = df["Churn Value"]
    features = df.drop(columns=[c for c in EXCLUDE_FROM_MODEL if c in df.columns])
    features = features.drop(columns=["Churn Value"], errors="ignore")

    numeric_cols = features.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = [
        c for c in features.columns if c not in numeric_cols and c != "Churn Value"
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", SimpleImputer(strategy="median"), numeric_cols),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_cols,
            ),
        ]
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )
    pipeline = Pipeline([("prep", preprocessor), ("model", model)])
    pipeline.fit(features, target)

    cat_names = pipeline.named_steps["prep"].named_transformers_["cat"].named_steps[
        "encoder"
    ].get_feature_names_out(categorical_cols)
    feature_names = list(numeric_cols) + list(cat_names)
    importances = pipeline.named_steps["model"].feature_importances_

    importance_df = (
        pd.DataFrame({"feature": feature_names, "importance": importances})
        .sort_values("importance", ascending=False)
        .head(15)
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(
        importance_df["feature"][::-1],
        importance_df["importance"][::-1],
        color="#4C78A8",
    )
    ax.set_title("Top 15 Feature Importances (Random Forest)")
    ax.set_xlabel("Importance")
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "feature_importance.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    return {
        "top_features": [
            {"feature": row.feature, "importance": round(float(row.importance), 4)}
            for row in importance_df.itertuples()
        ]
    }


def customer_segmentation(df: pd.DataFrame) -> dict:
    """Segment customers into high / medium / low churn risk using risk_score."""
    segmented = df.copy()
    segmented["risk_segment"] = pd.cut(
        segmented["risk_score"],
        bins=[0, 40, 65, 100],
        labels=["Low Risk", "Medium Risk", "High Risk"],
        include_lowest=True,
    )

    segment_stats = (
        segmented.groupby("risk_segment", observed=True)
        .agg(
            customers=("CustomerID", "count"),
            churn_rate=("Churn Value", "mean"),
            avg_tenure=("Tenure Months", "mean"),
            avg_monthly=("Monthly Charges", "mean"),
            avg_risk_score=("risk_score", "mean"),
        )
        .reset_index()
    )
    segment_stats["churn_rate"] = segment_stats["churn_rate"] * 100

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    order = ["Low Risk", "Medium Risk", "High Risk"]
    colors = ["#4C78A8", "#F58518", "#E45756"]

    axes[0].bar(
        segment_stats["risk_segment"],
        segment_stats["customers"],
        color=colors,
    )
    axes[0].set_title("Customers by Risk Segment")
    axes[0].set_ylabel("Count")
    axes[0].set_xlabel("Risk Segment")

    churn_by_seg = (
        segmented.groupby("risk_segment", observed=True)["Churn Value"]
        .mean()
        .reindex(order)
        * 100
    )
    axes[1].bar(order, churn_by_seg.values, color=colors)
    axes[1].set_title("Actual Churn Rate by Risk Segment")
    axes[1].set_ylabel("Churn Rate (%)")
    axes[1].set_xlabel("Risk Segment")

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "risk_segmentation.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    segmented[["CustomerID", "risk_score", "risk_segment", "Churn Label"]].to_csv(
        OUTPUT_DIR / "customer_risk_segments.csv", index=False
    )

    return {
        "segments": [
            {
                "segment": row.risk_segment,
                "customers": int(row.customers),
                "churn_rate_pct": round(float(row.churn_rate), 2),
                "avg_tenure_months": round(float(row.avg_tenure), 1),
                "avg_monthly_charges": round(float(row.avg_monthly), 2),
                "avg_risk_score": round(float(row.avg_risk_score), 1),
            }
            for row in segment_stats.itertuples()
        ]
    }


def churn_by_key_features(df: pd.DataFrame) -> dict:
    """Churn rate breakdown for interpretable business features."""
    breakdowns = {}
    for col in ["Contract", "Internet Service", "tenure_group", "Payment Method"]:
        grouped = (
            df.groupby(col, observed=True)["Churn Value"]
            .agg(["mean", "count"])
            .sort_values("mean", ascending=False)
        )
        breakdowns[col] = [
            {
                "category": str(idx),
                "churn_rate_pct": round(float(row["mean"]) * 100, 2),
                "count": int(row["count"]),
            }
            for idx, row in grouped.iterrows()
        ]
    return breakdowns


def main() -> None:
    _ensure_output_dir()
    df = pd.read_csv(INPUT_PATH)
    engineered = engineer_features(df)
    engineered.to_csv(ENGINEERED_PATH, index=False)

    stats = {
        "dataset_rows": len(engineered),
        "churn": churn_distribution(engineered),
        "correlations": correlation_heatmap(engineered),
        "feature_importance": feature_importance(engineered),
        "segmentation": customer_segmentation(engineered),
        "churn_breakdowns": churn_by_key_features(engineered),
        "added_features": [
            c
            for c in engineered.columns
            if c not in pd.read_csv(INPUT_PATH, nrows=1).columns
        ],
    }

    STATS_PATH.write_text(json.dumps(stats, indent=2))
    print(f"EDA complete. Outputs saved to: {OUTPUT_DIR}")
    print(f"Stats JSON: {STATS_PATH}")


if __name__ == "__main__":
    main()
