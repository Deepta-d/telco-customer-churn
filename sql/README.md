# Phase 2: SQL Analysis (MySQL)

Load the cleaned Telco churn dataset into MySQL and run business SQL queries.

## Prerequisites

- MySQL 8.0 running locally (service `MySQL80`)
- Python packages: `pip install -r requirements.txt`

## Quick Start

### Option A — Python (recommended, no PowerShell policy issues)

```powershell
cd "c:\Users\DELL\cursor demo\customer-churn"
python sql/setup_phase2.py
```

It will prompt for your MySQL password, or read it from `sql/.env`.

### Option B — Batch file

```powershell
cd "c:\Users\DELL\cursor demo\customer-churn"
.\sql\setup_phase2.bat
```

### Option C — PowerShell script (if blocked, see fix below)

```powershell
powershell -ExecutionPolicy Bypass -File ".\sql\setup_phase2.ps1" -Password "your_actual_password"
```

**Important:** Replace `your_actual_password` with your real MySQL root password — not the literal text `YOUR_MYSQL_PASSWORD`.

### 1. Configure MySQL credentials (optional)

```powershell
copy sql\.env.example sql\.env
```

Edit `sql/.env` and set your MySQL root password.

### 2. Prepare SQL-ready dataset

```powershell
python sql/prepare_sql_dataset.py
```

Output: `sql/telco_customers_sql_ready.csv` (68 columns)

### 3. Create database and load data

```powershell
python sql/load_to_mysql.py -p YOUR_MYSQL_PASSWORD
```

### 4. Run analysis queries

```powershell
python sql/run_queries.py
```

Or open `sql/analysis_queries.sql` in MySQL Workbench.

## One-command setup

```powershell
.\sql\setup_phase2.ps1 -Password "YOUR_MYSQL_PASSWORD"
```

## Queries Included

### Original (1–6)
1. Monthly churn rate
2. Churn by plan type
3. High-value customers churn rate
4. ARPU (overall + by plan)
5. Basic CLTV calculation
6. Window functions: running churn %, rank high-risk, tenure lifecycle, retention targets

### Added (7–38) — 32 queries
7–22: Basic — internet, payment, tenure, gender, cities, risk segment, revenue, add-ons, fiber/DSL, autopay, paperless, streaming, security, charge buckets, household, engagement quartiles, churn reasons, cohorts

23–38: Advanced — LAG, moving average, PERCENT_RANK, ROLLUP, subqueries, CASE segmentation, HAVING, FIRST_VALUE, correlated join, cumulative revenue, combo services, cohort retention, DENSE_RANK

### Validate queries

```powershell
python sql/validate_queries.py           # all 43 queries
python sql/validate_queries.py --from 7  # new queries only
python sql/run_queries.py --from 7       # run and print results
```

## Project Structure

```
sql/
├── prepare_sql_dataset.py
├── telco_customers_sql_ready.csv
├── schema.sql
├── load_to_mysql.py
├── powerbi_views.sql
├── analysis_queries.sql
├── run_queries.py
├── setup_phase2.ps1
├── .env.example
└── README.md
```

## Phase 4: Power BI MySQL Connection

After loading base data, create the Power BI view and ML score table:

```powershell
python sql/load_to_mysql.py
python powerbi/load_scores_to_mysql.py
```

Power BI Desktop: connect to `telco_churn.vw_powerbi_customers`.

See `powerbi/DASHBOARD_BUILD_GUIDE.md` for full dashboard build steps.
