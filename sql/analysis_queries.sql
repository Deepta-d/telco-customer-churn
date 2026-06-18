-- Telco Customer Churn — Phase 2 SQL Analysis
-- Database: telco_churn
-- Prerequisite: schema.sql + load_to_mysql.py

USE telco_churn;

-- =============================================================================
-- 1. MONTHLY CHURN RATE
-- Churn events grouped by calendar month (derived from join_date + tenure).
-- =============================================================================
SELECT
    churn_month,
    COUNT(*) AS churned_customers,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_all_churn,
    ROUND(
        COUNT(*) * 100.0 / (
            SELECT COUNT(*)
            FROM telco_customers
            WHERE join_month <= churn_month
        ),
        2
    ) AS monthly_churn_rate_pct
FROM telco_customers
WHERE churn_value = 1
  AND churn_month IS NOT NULL
GROUP BY churn_month
ORDER BY churn_month;


-- =============================================================================
-- 2. CHURN BY PLAN TYPE (Contract)
-- =============================================================================
SELECT
    plan_type,
    COUNT(*) AS total_customers,
    SUM(churn_value) AS churned_customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
FROM telco_customers
GROUP BY plan_type
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- 3. HIGH-VALUE CUSTOMERS CHURN RATE
-- High-value = top 25% CLTV or top 25% monthly charges
-- =============================================================================
SELECT
    CASE is_high_value
        WHEN 1 THEN 'High Value'
        ELSE 'Standard Value'
    END AS customer_tier,
    COUNT(*) AS total_customers,
    SUM(churn_value) AS churned_customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges,
    ROUND(AVG(cltv), 0) AS avg_cltv
FROM telco_customers
GROUP BY is_high_value
ORDER BY is_high_value DESC;


-- =============================================================================
-- 4. AVERAGE REVENUE PER USER (ARPU)
-- =============================================================================
SELECT
    ROUND(AVG(monthly_charges), 2) AS arpu_overall,
    ROUND(AVG(CASE WHEN churn_value = 0 THEN monthly_charges END), 2) AS arpu_retained,
    ROUND(AVG(CASE WHEN churn_value = 1 THEN monthly_charges END), 2) AS arpu_churned
FROM telco_customers;

SELECT
    plan_type,
    COUNT(*) AS customers,
    ROUND(AVG(monthly_charges), 2) AS arpu
FROM telco_customers
GROUP BY plan_type
ORDER BY arpu DESC;


-- =============================================================================
-- 5. CUSTOMER LIFETIME VALUE (basic calculation)
-- basic_cltv = monthly_charges * tenure_months
-- =============================================================================
SELECT
    ROUND(AVG(basic_cltv_calc), 2) AS avg_basic_cltv,
    ROUND(AVG(cltv), 2) AS avg_dataset_cltv,
    ROUND(AVG(basic_cltv_calc - cltv), 2) AS avg_cltv_gap
FROM telco_customers;

SELECT
    plan_type,
    COUNT(*) AS customers,
    ROUND(AVG(basic_cltv_calc), 2) AS avg_basic_cltv,
    ROUND(AVG(cltv), 2) AS avg_dataset_cltv
FROM telco_customers
GROUP BY plan_type
ORDER BY avg_basic_cltv DESC;


-- =============================================================================
-- ADVANCED: WINDOW FUNCTIONS
-- =============================================================================

-- =============================================================================
-- 6a. RUNNING CHURN % (cumulative churn share over calendar months)
-- =============================================================================
WITH monthly_churn AS (
    SELECT
        churn_month,
        COUNT(*) AS churned_count
    FROM telco_customers
    WHERE churn_value = 1
      AND churn_month IS NOT NULL
    GROUP BY churn_month
)
SELECT
    churn_month,
    churned_count,
    SUM(churned_count) OVER (ORDER BY churn_month) AS running_churned_total,
    ROUND(
        SUM(churned_count) OVER (ORDER BY churn_month) * 100.0
        / SUM(churned_count) OVER (),
        2
    ) AS running_churn_pct
FROM monthly_churn
ORDER BY churn_month;


-- =============================================================================
-- 6b. RANK HIGH-RISK CUSTOMERS
-- =============================================================================
SELECT
    customer_id,
    plan_type,
    tenure_months,
    monthly_charges,
    cltv,
    risk_score,
    risk_segment,
    churn_label,
    RANK() OVER (ORDER BY risk_score DESC) AS risk_rank,
    DENSE_RANK() OVER (ORDER BY risk_score DESC) AS risk_dense_rank,
    NTILE(10) OVER (ORDER BY risk_score DESC) AS risk_decile
FROM telco_customers
ORDER BY risk_rank
LIMIT 50;


-- =============================================================================
-- 6c. Running churn % by tenure month (lifecycle view)
-- =============================================================================
SELECT
    tenure_months,
    COUNT(*) AS customers_at_tenure,
    SUM(churn_value) AS churned,
    ROUND(AVG(churn_value) * 100, 2) AS tenure_churn_rate_pct,
    ROUND(
        SUM(SUM(churn_value)) OVER (ORDER BY tenure_months)
        * 100.0 / SUM(COUNT(*)) OVER (),
        2
    ) AS running_churn_share_pct
FROM telco_customers
GROUP BY tenure_months
ORDER BY tenure_months;


-- =============================================================================
-- 6d. Top 20 high-risk customers who have NOT churned (retention targets)
-- =============================================================================
SELECT
    customer_id,
    plan_type,
    monthly_charges,
    tenure_months,
    risk_score,
    risk_segment,
    RANK() OVER (ORDER BY risk_score DESC) AS risk_rank
FROM telco_customers
WHERE churn_value = 0
ORDER BY risk_score DESC
LIMIT 20;


-- =============================================================================
-- 7. CHURN BY INTERNET SERVICE TYPE
-- =============================================================================
SELECT
    internet_service,
    COUNT(*) AS total_customers,
    SUM(churn_value) AS churned,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges
FROM telco_customers
GROUP BY internet_service
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- 8. CHURN BY PAYMENT METHOD
-- =============================================================================
SELECT
    payment_method,
    COUNT(*) AS total_customers,
    SUM(churn_value) AS churned,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
FROM telco_customers
GROUP BY payment_method
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- 9. CHURN BY TENURE GROUP (New / Established / Loyal)
-- =============================================================================
SELECT
    tenure_group,
    COUNT(*) AS total_customers,
    SUM(churn_value) AS churned,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct,
    ROUND(AVG(tenure_months), 1) AS avg_tenure_months
FROM telco_customers
GROUP BY tenure_group
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- 10. CHURN BY GENDER AND SENIOR STATUS
-- =============================================================================
SELECT
    gender,
    senior_citizen,
    COUNT(*) AS total_customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
FROM telco_customers
GROUP BY gender, senior_citizen
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- 11. TOP 10 CITIES BY CUSTOMER COUNT WITH CHURN RATE
-- =============================================================================
SELECT
    city,
    state,
    COUNT(*) AS customers,
    SUM(churn_value) AS churned,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
FROM telco_customers
GROUP BY city, state
HAVING COUNT(*) >= 50
ORDER BY customers DESC
LIMIT 10;


-- =============================================================================
-- 12. AVERAGE TENURE AND TOTAL CHARGES BY PLAN TYPE
-- =============================================================================
SELECT
    plan_type,
    ROUND(AVG(tenure_months), 1) AS avg_tenure_months,
    ROUND(AVG(total_charges), 2) AS avg_total_charges,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges,
    COUNT(*) AS customers
FROM telco_customers
GROUP BY plan_type
ORDER BY avg_tenure_months DESC;


-- =============================================================================
-- 13. CHURN RATE BY RISK SEGMENT
-- =============================================================================
SELECT
    risk_segment,
    COUNT(*) AS customers,
    SUM(churn_value) AS churned,
    ROUND(AVG(churn_value) * 100, 2) AS actual_churn_rate_pct,
    ROUND(AVG(risk_score), 1) AS avg_risk_score
FROM telco_customers
GROUP BY risk_segment
ORDER BY actual_churn_rate_pct DESC;


-- =============================================================================
-- 14. TOTAL MONTHLY REVENUE — RETAINED VS CHURNED
-- =============================================================================
SELECT
    CASE churn_value WHEN 1 THEN 'Churned' ELSE 'Retained' END AS status,
    COUNT(*) AS customers,
    ROUND(SUM(monthly_charges), 2) AS total_monthly_revenue,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges
FROM telco_customers
GROUP BY churn_value
ORDER BY churn_value;


-- =============================================================================
-- 15. ADD-ON SERVICES IMPACT ON CHURN
-- =============================================================================
SELECT
    addon_services_count,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
FROM telco_customers
GROUP BY addon_services_count
ORDER BY addon_services_count;


-- =============================================================================
-- 16. FIBER VS DSL CHURN COMPARISON
-- =============================================================================
SELECT
    CASE
        WHEN internet_fiber = 1 THEN 'Fiber'
        WHEN internet_dsl = 1 THEN 'DSL'
        ELSE 'No Internet'
    END AS internet_category,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges
FROM telco_customers
GROUP BY internet_category
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- 17. AUTOPAY VS ELECTRONIC CHECK CHURN
-- =============================================================================
SELECT
    CASE
        WHEN is_autopay = 1 THEN 'Auto Pay'
        WHEN is_electronic_check = 1 THEN 'Electronic Check'
        ELSE 'Other Payment'
    END AS payment_category,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
FROM telco_customers
GROUP BY payment_category
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- 18. PAPERLESS BILLING IMPACT ON CHURN
-- =============================================================================
SELECT
    paperless_billing,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges
FROM telco_customers
GROUP BY paperless_billing;


-- =============================================================================
-- 19. STREAMING BUNDLE VS NO BUNDLE CHURN
-- =============================================================================
SELECT
    CASE has_streaming_bundle WHEN 1 THEN 'Has Both Streaming' ELSE 'No Full Bundle' END AS streaming_status,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
FROM telco_customers
GROUP BY has_streaming_bundle;


-- =============================================================================
-- 20. CUSTOMERS WITH ONLINE SECURITY — CHURN COMPARISON
-- =============================================================================
SELECT
    online_security,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
FROM telco_customers
GROUP BY online_security
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- 21. MONTHLY CHARGES DISTRIBUTION BY BUCKETS
-- =============================================================================
SELECT
    CASE
        WHEN monthly_charges < 35 THEN 'Low (<35)'
        WHEN monthly_charges < 70 THEN 'Medium (35-70)'
        WHEN monthly_charges < 100 THEN 'High (70-100)'
        ELSE 'Premium (100+)'
    END AS charge_bucket,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
FROM telco_customers
GROUP BY charge_bucket
ORDER BY MIN(monthly_charges);


-- =============================================================================
-- 22. FAMILY HOUSEHOLD VS SINGLE CUSTOMER CHURN
-- =============================================================================
SELECT
    CASE family_household WHEN 1 THEN 'Family Household' ELSE 'Single/No Dependents' END AS household_type,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct,
    ROUND(AVG(household_size_proxy), 1) AS avg_household_size
FROM telco_customers
GROUP BY family_household;


-- =============================================================================
-- 23. ENGAGEMENT SCORE QUARTILES VS CHURN
-- =============================================================================
SELECT
    engagement_quartile,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct,
    ROUND(MIN(engagement_score), 1) AS min_score,
    ROUND(MAX(engagement_score), 1) AS max_score
FROM (
    SELECT
        churn_value,
        engagement_score,
        NTILE(4) OVER (ORDER BY engagement_score) AS engagement_quartile
    FROM telco_customers
) scored
GROUP BY engagement_quartile
ORDER BY engagement_quartile;


-- =============================================================================
-- 24. TOP 10 CHURN REASONS (CHURNED CUSTOMERS ONLY)
-- =============================================================================
SELECT
    churn_reason,
    COUNT(*) AS customers,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_churned
FROM telco_customers
WHERE churn_value = 1
  AND churn_reason IS NOT NULL
  AND churn_reason <> 'Not Applicable'
GROUP BY churn_reason
ORDER BY customers DESC
LIMIT 10;


-- =============================================================================
-- 25. COHORT CHURN BY JOIN MONTH (first 12 cohorts)
-- =============================================================================
SELECT
    join_month,
    COUNT(*) AS cohort_size,
    SUM(churn_value) AS churned,
    ROUND(AVG(churn_value) * 100, 2) AS cohort_churn_rate_pct
FROM telco_customers
GROUP BY join_month
ORDER BY join_month
LIMIT 12;


-- =============================================================================
-- 26. LAG — MONTH-OVER-MONTH CHANGE IN CHURN COUNT (WINDOW FUNCTION)
-- =============================================================================
WITH monthly AS (
    SELECT
        churn_month,
        COUNT(*) AS churned_count
    FROM telco_customers
    WHERE churn_value = 1 AND churn_month IS NOT NULL
    GROUP BY churn_month
)
SELECT
    churn_month,
    churned_count,
    LAG(churned_count) OVER (ORDER BY churn_month) AS prev_month_churn,
    churned_count - LAG(churned_count) OVER (ORDER BY churn_month) AS mom_change
FROM monthly
ORDER BY churn_month
LIMIT 15;


-- =============================================================================
-- 27. 3-MONTH MOVING AVERAGE OF CHURN EVENTS (WINDOW FUNCTION)
-- =============================================================================
WITH monthly AS (
    SELECT
        churn_month,
        COUNT(*) AS churned_count
    FROM telco_customers
    WHERE churn_value = 1 AND churn_month IS NOT NULL
    GROUP BY churn_month
)
SELECT
    churn_month,
    churned_count,
    ROUND(
        AVG(churned_count) OVER (
            ORDER BY churn_month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS moving_avg_3mo
FROM monthly
ORDER BY churn_month
LIMIT 15;


-- =============================================================================
-- 28. PERCENTILE RANK OF MONTHLY CHARGES WITHIN PLAN TYPE
-- =============================================================================
SELECT
    customer_id,
    plan_type,
    monthly_charges,
    ROUND(PERCENT_RANK() OVER (PARTITION BY plan_type ORDER BY monthly_charges) * 100, 2) AS pct_rank_in_plan
FROM telco_customers
ORDER BY plan_type, pct_rank_in_plan DESC
LIMIT 20;


-- =============================================================================
-- 29. ROLLUP — CHURN BY PLAN TYPE AND INTERNET SERVICE
-- =============================================================================
SELECT
    IF(GROUPING(plan_type) = 1, 'ALL PLANS', plan_type) AS plan_type,
    IF(GROUPING(internet_service) = 1, 'ALL INTERNET', internet_service) AS internet_service,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
FROM telco_customers
GROUP BY plan_type, internet_service WITH ROLLUP
HAVING NOT (GROUPING(plan_type) = 0 AND GROUPING(internet_service) = 0 AND customers < 30)
ORDER BY plan_type, internet_service;


-- =============================================================================
-- 30. SUBQUERY — CHURN RATE FOR ABOVE-AVERAGE CLTV CUSTOMERS
-- =============================================================================
SELECT
    'Above Avg CLTV' AS segment,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct,
    ROUND(AVG(cltv), 0) AS avg_cltv
FROM telco_customers
WHERE cltv > (SELECT AVG(cltv) FROM telco_customers)
UNION ALL
SELECT
    'Below or Equal Avg CLTV',
    COUNT(*),
    ROUND(AVG(churn_value) * 100, 2),
    ROUND(AVG(cltv), 0)
FROM telco_customers
WHERE cltv <= (SELECT AVG(cltv) FROM telco_customers);


-- =============================================================================
-- 31. CASE-BASED CUSTOMER VALUE SEGMENTATION
-- =============================================================================
SELECT
    CASE
        WHEN is_high_value = 1 AND churn_value = 0 THEN 'High Value Retained'
        WHEN is_high_value = 1 AND churn_value = 1 THEN 'High Value Churned'
        WHEN is_high_value = 0 AND churn_value = 0 THEN 'Standard Retained'
        ELSE 'Standard Churned'
    END AS value_churn_segment,
    COUNT(*) AS customers,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly,
    ROUND(AVG(cltv), 0) AS avg_cltv
FROM telco_customers
GROUP BY value_churn_segment
ORDER BY customers DESC;


-- =============================================================================
-- 32. HAVING — CITIES WITH CHURN RATE ABOVE 30% (min 100 customers)
-- =============================================================================
SELECT
    city,
    state,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
FROM telco_customers
GROUP BY city, state
HAVING COUNT(*) >= 100 AND AVG(churn_value) > 0.30
ORDER BY churn_rate_pct DESC
LIMIT 10;


-- =============================================================================
-- 33. FIRST VALUE — HIGHEST MONTHLY CHARGE PER PLAN TYPE (WINDOW)
-- =============================================================================
SELECT DISTINCT
    plan_type,
    FIRST_VALUE(customer_id) OVER (
        PARTITION BY plan_type ORDER BY monthly_charges DESC
    ) AS top_spender_id,
    FIRST_VALUE(monthly_charges) OVER (
        PARTITION BY plan_type ORDER BY monthly_charges DESC
    ) AS max_monthly_charge
FROM telco_customers;


-- =============================================================================
-- 34. CORRELATED SUBQUERY — CUSTOMERS PAYING MORE THAN PLAN AVERAGE
-- =============================================================================
SELECT
    c.customer_id,
    c.plan_type,
    c.monthly_charges,
    ROUND(plan_avg.avg_charge, 2) AS plan_avg_charge,
    ROUND(c.monthly_charges - plan_avg.avg_charge, 2) AS above_avg_by
FROM telco_customers c
JOIN (
    SELECT plan_type, AVG(monthly_charges) AS avg_charge
    FROM telco_customers
    GROUP BY plan_type
) plan_avg ON c.plan_type = plan_avg.plan_type
WHERE c.monthly_charges > plan_avg.avg_charge
  AND c.churn_value = 1
ORDER BY above_avg_by DESC
LIMIT 15;


-- =============================================================================
-- 35. CUMULATIVE REVENUE BY TENURE MONTH (RUNNING SUM WINDOW)
-- =============================================================================
SELECT
    tenure_months,
    COUNT(*) AS customers,
    ROUND(SUM(monthly_charges), 2) AS monthly_revenue,
    ROUND(
        SUM(SUM(monthly_charges)) OVER (ORDER BY tenure_months),
        2
    ) AS cumulative_revenue
FROM telco_customers
GROUP BY tenure_months
ORDER BY tenure_months
LIMIT 20;


-- =============================================================================
-- 36. TECH SUPPORT AND DEVICE PROTECTION COMBO CHURN
-- =============================================================================
SELECT
    tech_support,
    device_protection,
    COUNT(*) AS customers,
    ROUND(AVG(churn_value) * 100, 2) AS churn_rate_pct
FROM telco_customers
WHERE internet_service <> 'No'
GROUP BY tech_support, device_protection
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- 37. JOIN MONTH COHORT RETENTION — CUSTOMERS STILL ACTIVE
-- =============================================================================
SELECT
    join_month,
    COUNT(*) AS joined,
    SUM(CASE WHEN churn_value = 0 THEN 1 ELSE 0 END) AS still_active,
    ROUND(SUM(CASE WHEN churn_value = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS retention_rate_pct
FROM telco_customers
GROUP BY join_month
ORDER BY join_month
LIMIT 12;


-- =============================================================================
-- 38. DENSE_RANK — TOP CLTV CUSTOMERS PER RISK SEGMENT
-- =============================================================================
SELECT
    customer_id,
    risk_segment,
    cltv,
    monthly_charges,
    churn_label,
    cltv_rank_in_segment
FROM (
    SELECT
        customer_id,
        risk_segment,
        cltv,
        monthly_charges,
        churn_label,
        DENSE_RANK() OVER (PARTITION BY risk_segment ORDER BY cltv DESC) AS cltv_rank_in_segment
    FROM telco_customers
) ranked
WHERE cltv_rank_in_segment <= 5;
