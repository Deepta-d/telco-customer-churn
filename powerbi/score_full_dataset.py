"""Score all Telco customers with the Phase 3 CatBoost best model."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "Telco_customer_churn_engineered.csv"
MODEL_PATH = ROOT / "ml_outputs" / "models" / "best_model.joblib"
CONFIG_PATH = ROOT / "ml_outputs" / "splits" / "feature_config.json"
OUTPUT_PATH = ROOT / "ml_outputs" / "churn_scores_full.csv"


def risk_tier(score_pct: float) -> str:
    if score_pct < 40:
        return "Low"
    if score_pct < 70:
        return "Medium"
    return "High"


def load_feature_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def prepare_features(df: pd.DataFrame, exclude_cols: set[str]) -> pd.DataFrame:
    drop_cols = [c for c in exclude_cols if c in df.columns]
    return df.drop(columns=drop_cols)


def score_full_dataset(
    data_path: Path = DATA_PATH,
    model_path: Path = MODEL_PATH,
    output_path: Path = OUTPUT_PATH,
) -> pd.DataFrame:
    if not data_path.exists():
        raise FileNotFoundError(f"Engineered data not found: {data_path}")
    if not model_path.exists():
        raise FileNotFoundError(
            f"Best model not found: {model_path}. Run notebooks 01-02 first."
        )

    config = load_feature_config()
    exclude_cols = set(config["exclude_cols"])

    df = pd.read_csv(data_path)
    customer_ids = df["CustomerID"]
    X = prepare_features(df, exclude_cols)

    model = joblib.load(model_path)
    proba = model.predict_proba(X)[:, 1]
    churn_risk_pct = (proba * 100).round(2)

    scores = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "churn_risk_pct": churn_risk_pct,
            "risk_tier": [risk_tier(s) for s in churn_risk_pct],
            "predicted_churn": (proba >= 0.5).astype(int),
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(output_path, index=False)

    print(f"Scored {len(scores):,} customers -> {output_path}")
    print(scores["risk_tier"].value_counts().to_string())
    return scores


if __name__ == "__main__":
    try:
        score_full_dataset()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
