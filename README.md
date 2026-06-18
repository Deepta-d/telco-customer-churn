# Telco Customer Churn Analytics

End-to-end churn analytics on the IBM Telco dataset (7,043 customers): Python EDA, MySQL BI, machine learning, Power BI dashboards, and a GenAI Streamlit copilot.

## Phases

| Phase | Focus | Key paths |
|-------|--------|-----------|
| **1** | Cleaning, feature engineering, EDA | `clean_data.py`, `feature_engineering.py`, `eda_analysis.py`, `eda_outputs/` |
| **2** | MySQL analytics (43 SQL queries) | `sql/`, see `sql/README.md` |
| **3** | 10 classifiers, SHAP, risk scores | `notebooks/01–03`, `ml_outputs/` |
| **4** | Power BI executive dashboard | `powerbi/`, see `powerbi/DASHBOARD_BUILD_GUIDE.md` |
| **5** | Natural-language Q&A copilot | `genai/`, `streamlit/churn_copilot.py`, see `genai/README.md` |

Full write-up: [`PROJECT_RESEARCH_REPORT.md`](PROJECT_RESEARCH_REPORT.md)

## Quick start

### 1. Install

```powershell
pip install -r requirements.txt
```

### 2. Configure secrets (local only)

```powershell
copy sql\.env.example sql\.env
copy genai\.env.example genai\.env
```

Edit both files with your **MySQL password**. For Phase 5, set `LLM_PROVIDER=ollama` or add `OPENAI_API_KEY` — **never commit `.env` files**.

### 3. Run the pipeline

```powershell
# Phase 1
python clean_data.py
python feature_engineering.py
python eda_analysis.py

# Phase 2
python sql/prepare_sql_dataset.py
python sql/setup_phase2.py

# Phase 3 — run notebooks in order
jupyter notebook notebooks/

# Phase 4
python powerbi/setup_phase4.py

# Phase 5
streamlit run streamlit/churn_copilot.py
```

## Results highlights

- **Churn rate:** 26.54%
- **Top drivers:** contract type, tenure, internet service, payment method
- **Best model:** CatBoost — ROC-AUC **0.857** (test set)
- **Outputs:** EDA charts in `eda_outputs/`, ML metrics in `ml_outputs/phase3_summary.json`

## Project structure

```
customer-churn/
├── Telco_customer_churn.xlsx      # Source dataset
├── clean_data.py                  # Phase 1 scripts
├── feature_engineering.py
├── eda_analysis.py
├── eda_outputs/                   # EDA charts + stats
├── sql/                           # Phase 2 MySQL layer
├── notebooks/                     # Phase 3 & 5 notebooks
├── ml_outputs/                    # Metrics, plots (models via notebooks)
├── powerbi/                       # Phase 4 dashboard assets
├── genai/                         # Phase 5 agent
├── streamlit/                     # Phase 5 UI
└── PROJECT_RESEARCH_REPORT.md
```

## Requirements

- Python 3.10+
- MySQL 8.0 (Phases 2, 4, 5)
- Power BI Desktop (Phase 4 dashboard build)
- Ollama or OpenAI API key (Phase 5)

## License

Educational / portfolio use. IBM Telco Customer Churn dataset — see dataset terms for redistribution.
