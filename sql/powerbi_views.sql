-- Power BI views and ML score table (Phase 4)
-- Run after telco_customers is loaded:
--   mysql -u root -p telco_churn < sql/powerbi_views.sql

USE telco_churn;

DROP TABLE IF EXISTS churn_scores_full;
CREATE TABLE churn_scores_full (
    customer_id     VARCHAR(20)   NOT NULL PRIMARY KEY,
    churn_risk_pct  DECIMAL(6, 2) NOT NULL,
    risk_tier       VARCHAR(10)   NOT NULL,
    predicted_churn TINYINT       NOT NULL,
    INDEX idx_risk_tier (risk_tier),
    INDEX idx_churn_risk_pct (churn_risk_pct)
) ENGINE=InnoDB;

DROP VIEW IF EXISTS vw_powerbi_customers;
CREATE VIEW vw_powerbi_customers AS
SELECT
    c.customer_id,
    c.customer_count,
    c.country,
    c.state,
    c.city,
    c.zip_code,
    c.lat_long,
    c.latitude,
    c.longitude,
    c.gender,
    c.senior_citizen,
    c.partner,
    c.dependents,
    c.tenure_months,
    c.phone_service,
    c.multiple_lines,
    c.internet_service,
    c.online_security,
    c.online_backup,
    c.device_protection,
    c.tech_support,
    c.streaming_tv,
    c.streaming_movies,
    c.contract,
    c.paperless_billing,
    c.payment_method,
    c.monthly_charges,
    c.total_charges,
    c.churn_label,
    c.churn_value,
    c.churn_score,
    c.cltv,
    c.churn_reason,
    c.tenure_group,
    c.avg_monthly_spend,
    c.charge_drift,
    c.cltv_per_month,
    c.is_senior,
    c.has_partner,
    c.has_dependents,
    c.household_size_proxy,
    c.family_household,
    c.contract_ordinal,
    c.is_month_to_month,
    c.is_paperless,
    c.is_autopay,
    c.is_electronic_check,
    c.internet_fiber,
    c.internet_dsl,
    c.no_internet,
    c.has_phone,
    c.has_multiple_lines,
    c.addon_services_count,
    c.streaming_services_count,
    c.total_services_count,
    c.has_streaming_bundle,
    c.high_monthly_charge,
    c.engagement_score,
    c.risk_score,
    c.plan_type,
    c.reference_date,
    c.join_date,
    c.join_month,
    c.churn_date,
    c.churn_month,
    c.is_high_value,
    c.basic_cltv_calc,
    c.risk_segment,
    s.churn_risk_pct,
    s.risk_tier,
    s.predicted_churn,
    c.churn_value AS is_churned,
    CASE WHEN c.senior_citizen = 'Yes' THEN 'Senior' ELSE 'Non-Senior' END AS age_segment,
    CASE
        WHEN c.total_services_count <= 2 THEN 'Low (0-2)'
        WHEN c.total_services_count <= 5 THEN 'Medium (3-5)'
        ELSE 'High (6+)'
    END AS usage_band,
    COALESCE(c.tenure_group, 'Unknown') AS tenure_band,
    c.city AS region,
    CASE
        WHEN c.churn_label = 'No' AND s.churn_risk_pct >= 70 THEN c.monthly_charges
        ELSE 0
    END AS revenue_at_risk,
    top10.top10_risk_rank
FROM telco_customers c
LEFT JOIN churn_scores_full s ON c.customer_id = s.customer_id
LEFT JOIN (
    SELECT customer_id, rn AS top10_risk_rank
    FROM (
        SELECT
            c2.customer_id,
            ROW_NUMBER() OVER (ORDER BY s2.churn_risk_pct DESC) AS rn
        FROM telco_customers c2
        INNER JOIN churn_scores_full s2 ON c2.customer_id = s2.customer_id
        WHERE c2.churn_label = 'No'
    ) ranked
    WHERE rn <= 10
) top10 ON c.customer_id = top10.customer_id;
