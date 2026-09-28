-- Grain: one eligible paid subscription per complete observed calendar month.

CREATE OR REPLACE VIEW analytics.mart_subscriber_retention AS
WITH period AS (
    SELECT period_end
    FROM core.dataset_periods
    LIMIT 1
),
observations AS (
    SELECT
        a.user_id,
        a.subscription_id,
        DATE_TRUNC('month', a.subscription_started_at)::DATE AS cohort_month,
        activity_month::DATE AS activity_month,
        (
            (EXTRACT(YEAR FROM activity_month) - EXTRACT(YEAR FROM a.subscription_started_at)) * 12
            + EXTRACT(MONTH FROM activity_month)
            - EXTRACT(MONTH FROM a.subscription_started_at)
        )::INTEGER AS month_number,
        a.sales_channel,
        a.plan,
        a.activated_7d
    FROM analytics.mart_subscriber_activation AS a
    CROSS JOIN period AS p
    CROSS JOIN LATERAL GENERATE_SERIES(
        DATE_TRUNC('month', a.subscription_started_at),
        DATE_TRUNC('month', p.period_end - INTERVAL '1 day'),
        INTERVAL '1 month'
    ) AS activity_month
),
session_metrics AS (
    SELECT
        subscription_id,
        DATE_TRUNC('month', started_at)::DATE AS activity_month,
        COUNT(*) AS successful_sessions
    FROM core.proxy_sessions
    WHERE connection_status = 'success'
    GROUP BY subscription_id, DATE_TRUNC('month', started_at)::DATE
)
SELECT
    o.*,
    COALESCE(s.successful_sessions, 0) AS successful_sessions,
    o.month_number = 0 OR COALESCE(s.successful_sessions, 0) > 0 AS retained
FROM observations AS o
LEFT JOIN session_metrics AS s USING (subscription_id, activity_month);

COMMENT ON VIEW analytics.mart_subscriber_retention IS
    'Calendar-month usage retention for eligible new paid subscribers; M0 is the cohort baseline.';
