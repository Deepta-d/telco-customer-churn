# Telco Churn Power BI Dashboard — Build Guide

Step-by-step instructions to build **Telco_Churn_Dashboard.pbix** from project artifacts.

---

## Prerequisites

1. [Power BI Desktop](https://powerbi.microsoft.com/desktop/) installed
2. Phase 4 data prepared (run from project root):

```powershell
python powerbi/setup_phase4.py
```

This generates:
- `ml_outputs/churn_scores_full.csv` — CatBoost scores for all 7,043 customers
- `powerbi/telco_churn_powerbi.csv` — unified dashboard dataset
- MySQL view `telco_churn.vw_powerbi_customers` (if MySQL is configured)

---

## Part 1 — Import Data

### Option A: CSV (recommended for sharing / offline demo)

1. Open Power BI Desktop → **Get data** → **Text/CSV**
2. Select `powerbi/telco_churn_powerbi.csv`
3. Click **Transform Data** and apply:

| Column | Type |
|--------|------|
| `monthly_charges`, `total_charges`, `revenue_at_risk` | Decimal |
| `churn_risk_pct` | Fixed decimal |
| `reference_date`, `join_date`, `churn_date` | Date |
| `top10_risk_rank` | Whole number |

4. **Replace errors** on numeric columns (if any)
5. Rename query to `telco_churn_powerbi`
6. **Close & Apply**

### Option B: MySQL (live refresh)

1. Ensure MySQL is running and base data is loaded:

```powershell
python sql/load_to_mysql.py
python powerbi/load_scores_to_mysql.py
```

2. **Get data** → **MySQL database**
3. Server: `localhost`, Database: `telco_churn`
4. Select view: `vw_powerbi_customers`
5. Apply same Power Query type transforms as Option A
6. Rename query to `telco_churn_powerbi`

> Use **one** data source per report. DAX in `dax_measures.dax` assumes table name `telco_churn_powerbi`.

---

## Part 2 — Theme & Model

### Import theme

1. **View** → **Themes** → **Browse for themes**
2. Select `powerbi/theme/TelcoChurnTheme.json`

### Hide columns (optional)

In **Model view**, hide technical columns from report view:
`lat_long`, `customer_count`, `is_senior`, `has_partner`, etc.

Keep visible: `customer_id`, `city`, `state`, `plan_type`, `gender`, `churn_label`, `churn_risk_pct`, `monthly_charges`, `tenure_months`, `internet_service`, `join_month`, `usage_band`, `age_segment`, `top10_risk_rank`.

### Custom sort — Plan type

1. Select `plan_type` column → **Column tools** → **Sort by column** → create sort order:
   - Month-to-month = 1
   - One year = 2
   - Two year = 3

Or use **Model** → sort `contract` similarly.

### Add DAX measures

1. **Modeling** → **New measure**
2. Copy measures from `powerbi/dax_measures.dax`
3. Verify baseline KPIs (no filters):
   - Total Customers = **7,043**
   - Churn Rate % ≈ **26.54%**

---

## Part 3 — Global Slicers (all pages)

Create a **left panel** (width ~240px) on Page 1, then sync to all pages.

| Slicer | Field | Style |
|--------|-------|-------|
| Region | `city` (or `state` → drill in matrix) | List, multi-select |
| Plan | `plan_type` | Dropdown |
| Gender | `gender` | Tiles or dropdown |

**Sync slicers:**
1. Select all three slicers on Page 1
2. **View** → **Sync slicers**
3. Check all 4 report pages for each slicer
4. Copy slicers to other pages OR sync from Page 1 only (visible on all)

---

## Part 4 — Page Layouts

### Page 1: Executive Summary

**Canvas:** 16:9, background `#F4F6F8`

| Visual | Type | Fields / Config |
|--------|------|-----------------|
| Title | Text box | "Telco Churn Command Center" |
| KPI 1 | Card | `Total Customers` |
| KPI 2 | Card | `Churn Rate %` — format as %, 1 decimal |
| KPI 3 | Card | `Monthly Revenue Loss` — currency |
| KPI 4 | Card | `Revenue at Risk` |
| KPI 5 | Card | `High Risk Customers` |
| Donut | Donut chart | Legend: `churn_label`, Values: `Total Customers` |
| Trend | Line chart | Axis: `join_month`, Values: `Churn Rate by Join Month %` |
| **Top 10 At Risk** | **Table** | See below |

#### Top 10 Customers at Risk (must-have)

**Table visual fields:**
- `customer_id`
- `churn_risk_pct` (format %)
- `monthly_charges` (currency)
- `plan_type`
- `city`
- `tenure_months`
- `internet_service`

**Filters (Filters pane):**
- `churn_label` = **No** (active customers only)
- `top10_risk_rank` is not blank OR use **Top N** filter: Top 10 by `churn_risk_pct` descending

**Conditional formatting:**
- Data bars on `churn_risk_pct` (red gradient)
- Background on `monthly_charges` (teal)

Enable **Export data** on this visual (Format → General → Allow export).

---

### Page 2: Churn Analysis

| Visual | Type | Config |
|--------|------|--------|
| Churn by age | Clustered bar | Axis: `age_segment`, Values: `Churn Rate %` |
| Churn by plan | Clustered bar | Axis: `plan_type`, Values: `Churn Rate %` |
| Churn by region | Bar chart | Axis: `city` (Top 10 by count), Values: `Churn Rate %` |
| Segment matrix | Matrix | Rows: `state` → `city` → `plan_type`, Values: `Churn Rate %`, `Total Customers` |
| Internet mix | 100% stacked bar | Axis: `internet_service`, Legend: `churn_label`, Values: count |
| High risk card | Card | `Active High Risk Customers` |

**Drill-down:** Enable on matrix and bar charts (drill mode icon). Double-click `California` → cities → plans.

**Map (optional):** Filled map with `city`, `latitude`, `longitude`, color = `Churn Rate %`, size = `Total Customers`.

---

### Page 3: Revenue Insights

| Visual | Type | Config |
|--------|------|--------|
| ARPU KPI | Card | `ARPU` |
| ARPU by plan | Clustered column | Axis: `plan_type`, Values: `ARPU` |
| Revenue vs churn | Combo chart | X: `join_month`, Column: `Total Monthly Revenue`, Line: `Churn Rate %` |
| Risk scatter | Scatter | X: `monthly_charges`, Y: `churn_risk_pct`, Legend: `churn_label` |
| Revenue loss breakdown | Clustered bar | Axis: `plan_type`, Values: `Monthly Revenue Loss` |
| ARPU table | Table | `plan_type`, `age_segment`, `ARPU`, `Churn Rate %` |

---

### Page 4: Customer Behavior

| Visual | Type | Config |
|--------|------|--------|
| Usage vs churn | Clustered column | Axis: `usage_band`, Values: `Churn Rate %` |
| Tenure vs churn | Line chart | Axis: `tenure_band`, Values: `Churn Rate %` |
| Engagement | Scatter | X: `engagement_score`, Y: `churn_risk_pct`, Legend: `churn_label` |
| Tenure distribution | Clustered column | Axis: `tenure_months` (bins of 12), Legend: `churn_label` |
| Decomposition tree | Decomposition tree | Analyze: `Churn Rate %`, Explain by: `plan_type`, `internet_service`, `payment_method` |

---

## Part 5 — Drill-Through Page

1. Add hidden page: **Customer Detail**
2. Add table/cards: `customer_id`, `gender`, `plan_type`, `monthly_charges`, `tenure_months`, `churn_risk_pct`, `churn_label`, `churn_reason`, all service columns
3. On any page, right-click a visual → **Drill through** → **Customer Detail**
4. Add `customer_id` to drill-through fields on source visuals

---

## Part 6 — Bookmarks & Navigation

### Bookmarks

| Bookmark | Action |
|----------|--------|
| All Customers | Clear all slicer selections |
| High Risk Only | Filter `churn_risk_pct` >= 70 |
| Churned Only | Filter `churn_label` = Yes |

Create buttons on each page linked to bookmarks and page navigation (Page 1–4).

### Page navigator

Insert **Buttons** → **Navigator** → select all 4 pages.

---

## Part 7 — Save & Export

1. **File** → **Save as** → `powerbi/Telco_Churn_Dashboard.pbix`
2. Export screenshots:
   - **File** → **Export** → **Export as PDF** OR screenshot each page
   - Save to `powerbi/screenshots/`:
     - `01_executive_summary.png`
     - `02_churn_analysis.png`
     - `03_revenue_insights.png`
     - `04_customer_behavior.png`

3. Validate with:

```powershell
python powerbi/validate_powerbi_data.py
```

---

## Data Field Mapping Reference

| Dashboard term | Column |
|----------------|--------|
| Region | `city` (display as City/Region) |
| Plan | `plan_type` |
| Gender | `gender` |
| Age segment | `age_segment` (Senior / Non-Senior) |
| Usage | `usage_band` (from `total_services_count`) |
| Revenue loss | `Monthly Revenue Loss` measure |
| High risk | `churn_risk_pct` >= 70 or `risk_tier` = High |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Churn rate ≠ 26.54% | Check slicers are cleared; verify 7,043 rows loaded |
| Top 10 shows churned customers | Add filter `churn_label = No` |
| MySQL view empty | Run `python sql/load_to_mysql.py` then `python powerbi/load_scores_to_mysql.py` |
| Missing `churn_risk_pct` | Run `python powerbi/setup_phase4.py --rescore` |

---

## Estimated build time

| Step | Time |
|------|------|
| Import + measures | 45 min |
| Page 1 (Executive + Top 10) | 45 min |
| Pages 2–4 | 90 min |
| Drill-through + bookmarks | 30 min |
| **Total** | **~3 hours**
