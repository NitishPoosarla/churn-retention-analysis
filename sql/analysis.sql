-- 01-telco-churn — sql/analysis.sql
-- Reproduces the headline metrics from telco_clean.csv (UTF-8, header included).
--
-- How to load (SQLite):
--   .mode csv
--   .import data/processed/telco_clean.csv churn
-- (create the table manually first if your SQLite build won't type it,
--  e.g. use: csv to sqlite3 via a one-liner pandas export)
-- How to load (BigQuery): upload telco_clean.csv as table `churn`
--   (month-to-month churn col: churn_flag 1/0, monthly_charges numeric).

-- Overall churn facts
SELECT COUNT(*) AS total_customers,
       SUM(churn_flag) AS churners,
       ROUND(SUM(churn_flag) * 100.0 / COUNT(*), 1) AS churn_rate_pct,
       ROUND(SUM(CASE WHEN churn_flag = 1 THEN monthly_charges ELSE 0 END), 2)
         AS mrr_at_risk
FROM churn;

-- Churn by contract type
SELECT contract,
       COUNT(*) AS customers,
       ROUND(SUM(churn_flag) * 100.0 / COUNT(*), 1) AS churn_rate_pct
FROM churn
GROUP BY contract
ORDER BY churn_rate_pct DESC;

-- Churn by payment method
SELECT paymentmethod,
       COUNT(*) AS customers,
       ROUND(SUM(churn_flag) * 100.0 / COUNT(*), 1) AS churn_rate_pct
FROM churn
GROUP BY paymentmethod
ORDER BY churn_rate_pct DESC;

-- Median tenure (churners vs stayers) — BigQuery: PERCENTILE_CONT
-- SQLite approx via avg of middle row not trivial; BigQuery example below.
-- SELECT churn_flag,
--        PERCENTILE_CONT(tenure, 0.5) OVER (PARTITION BY churn_flag) AS med_tenure
-- FROM churn LIMIT 100;  -- see BigQuery docs for the exact form
