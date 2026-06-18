# Phase 4 — Power BI Dashboard

Creative Telco churn dashboard data layer and build assets.

## Quick start

```powershell
python powerbi/setup_phase4.py
python powerbi/validate_powerbi_data.py
```

Then open **Power BI Desktop** and follow [DASHBOARD_BUILD_GUIDE.md](DASHBOARD_BUILD_GUIDE.md).

## Artifacts

| File | Purpose |
|------|---------|
| `telco_churn_powerbi.csv` | Primary import (7,043 rows, 78 columns) |
| `dax_measures.dax` | Copy-paste DAX measures |
| `theme/TelcoChurnTheme.json` | Custom executive theme |
| `load_scores_to_mysql.py` | Load ML scores + `vw_powerbi_customers` view |
| `validate_powerbi_data.py` | Pre-build data checks |

## MySQL live connection

```powershell
python sql/load_to_mysql.py
python powerbi/load_scores_to_mysql.py
```

Connect Power BI to `telco_churn.vw_powerbi_customers`.

## `.pbix` file

`Telco_Churn_Dashboard.pbix` must be assembled in Power BI Desktop (binary format). Save to this folder after following the build guide.
