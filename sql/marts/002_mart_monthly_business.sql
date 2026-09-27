-- Grain: one row per complete calendar month.

CREATE OR REPLACE VIEW analytics.mart_monthly_business AS
WITH period AS (
    SELECT period_start, period_end
    FROM core.dataset_periods
    LIMIT 1
),
months AS (
    SELECT
        month_start,
        month_start + INTERVAL '1 month' AS month_end
    FROM period AS p
    CROSS JOIN LATERAL GENERATE_SERIES(
        DATE_TRUNC('month', p.period_start),
        DATE_TRUNC('month', p.period_end - INTERVAL '1 day'),
        INTERVAL '1 month'
    ) AS month_start
    WHERE month_start >= p.period_start
      AND month_start + INTERVAL '1 month' <= p.period_end
),
subscription_metrics AS (
    SELECT
        m.month_start,
        COUNT(DISTINCT sub.user_id) FILTER (
            WHERE sub.starts_at < m.month_end
              AND (sub.ends_at IS NULL OR sub.ends_at >= m.month_start)
        ) AS active_paid_subscribers,
        COUNT(DISTINCT sub.user_id) FILTER (
            WHERE sub.starts_at >= m.month_start AND sub.starts_at < m.month_end
        ) AS new_paid_users,
        COUNT(DISTINCT sub.user_id) FILTER (
            WHERE sub.ends_at >= m.month_start AND sub.ends_at < m.month_end
        ) AS churned_users,
        COALESCE(SUM(
            CASE sub.plan
                WHEN 'one_month' THEN sub.price_rub
                WHEN 'three_months' THEN sub.price_rub / 3.0
                WHEN 'twelve_months' THEN sub.price_rub / 12.0
            END
        ) FILTER (
            WHERE sub.starts_at < m.month_end
              AND (sub.ends_at IS NULL OR sub.ends_at >= m.month_end)
        ), 0) AS normalized_mrr_rub
    FROM months AS m
    CROSS JOIN core.subscriptions AS sub
    JOIN core.users AS u USING (user_id)
    WHERE NOT u.is_internal
    GROUP BY m.month_start
),
session_metrics AS (
    SELECT
        m.month_start,
        COUNT(DISTINCT s.user_id) FILTER (
            WHERE s.connection_status = 'success'
        ) AS monthly_active_paid_users,
        COUNT(DISTINCT s.user_id) FILTER (
            WHERE s.connection_status = 'success'
              AND sub.starts_at < p.period_start
              AND (sub.ends_at IS NULL OR sub.ends_at >= p.period_end)
        ) AS regular_paid_users,
        COUNT(*) FILTER (WHERE s.connection_status = 'failed')::NUMERIC
            / NULLIF(COUNT(*), 0) AS connection_failure_rate,
        COALESCE(SUM(s.bytes_down + s.bytes_up) FILTER (
            WHERE s.connection_status = 'success'
        ), 0) / 1000000000.0 AS traffic_gb
    FROM months AS m
    CROSS JOIN period AS p
    LEFT JOIN core.proxy_sessions AS s
        ON s.started_at >= m.month_start AND s.started_at < m.month_end
    LEFT JOIN core.subscriptions AS sub USING (subscription_id)
    GROUP BY m.month_start
),
payment_metrics AS (
    SELECT
        m.month_start,
        COALESCE(SUM(pay.amount_rub) FILTER (
            WHERE pay.payment_status = 'succeeded'
        ), 0) AS cash_revenue_rub
    FROM months AS m
    LEFT JOIN core.payments AS pay
        ON pay.paid_at >= m.month_start AND pay.paid_at < m.month_end
    GROUP BY m.month_start
)
SELECT
    m.month_start::DATE AS month_start,
    sm.active_paid_subscribers,
    se.monthly_active_paid_users,
    se.regular_paid_users,
    sm.new_paid_users,
    sm.churned_users,
    pay.cash_revenue_rub,
    sm.normalized_mrr_rub,
    se.connection_failure_rate,
    se.traffic_gb
FROM months AS m
JOIN subscription_metrics AS sm USING (month_start)
JOIN session_metrics AS se USING (month_start)
JOIN payment_metrics AS pay USING (month_start)
ORDER BY m.month_start;

COMMENT ON VIEW analytics.mart_monthly_business IS
    'Monthly paid subscriber base, 435-user regular core, revenue and proxy usage.';
